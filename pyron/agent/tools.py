import os
import sys
import shlex
import signal
import subprocess
import json
import difflib
from pathlib import Path
from typing import Any

TOOL_DIR = Path.home() / ".pyron" / "workspace"
SIMPLE_COMMANDS = {"mkdir", "touch", "ls", "echo", "cat", "cp", "mv", "rm", "pwd", "whoami", "date", "which", "printf", "dirname", "basename", "realpath", "readlink"}

FAST_PATH_TIMEOUT = 10
NORMAL_TIMEOUT = 60
LONG_TIMEOUT = 300

def _ensure_workspace():
    TOOL_DIR.mkdir(parents=True, exist_ok=True)

class ToolResult:
    def __init__(self, success: bool, output: str, error: str = "", exit_code: int = 0):
        self.success = success
        self.output = output
        self.error = error
        self.exit_code = exit_code

    def to_dict(self) -> dict:
        return {"success": self.success, "output": self.output, "error": self.error, "exit_code": self.exit_code}

    @property
    def is_real_failure(self) -> bool:
        if self.exit_code != 0:
            return True
        if self.error and "timed out" in self.error.lower():
            return True
        if self.error and "killed" in self.error.lower():
            return True
        if self.error and "permission denied" in self.error.lower():
            return True
        if self.error and "not found" in self.error.lower() and "pyron" not in self.error.lower():
            return True
        return False

def _is_simple_command(command: str) -> bool:
    cmd = command.strip().split()[0] if command.strip() else ""
    return cmd in SIMPLE_COMMANDS

def _resolve_workdir(workdir: str | None = None) -> str:
    _ensure_workspace()
    return workdir or str(TOOL_DIR)

def _kill_process_group(proc: subprocess.Popen):
    try:
        pgid = os.getpgid(proc.pid)
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            proc.kill()
        except Exception:
            pass

def bash_command(command: str, workdir: str | None = None, sandbox: bool = False) -> ToolResult:
    cwd = _resolve_workdir(workdir)
    is_simple = _is_simple_command(command)
    timeout = FAST_PATH_TIMEOUT if is_simple else NORMAL_TIMEOUT

    if sandbox:
        command = f"firejail --quiet --net=none --noroot bash -c {shlex.quote(command)} 2>/dev/null || {command}"

    try:
        proc = subprocess.Popen(
            ["bash", "-c", command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
            preexec_fn=os.setsid,
        )

        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            _kill_process_group(proc)
            stdout, stderr = proc.communicate()
            output = (stdout or "") + (stderr or "")
            return ToolResult(False, output[:10000], f"Command timed out after {timeout}s", exit_code=-1)

        exit_code = proc.returncode
        output = stdout or ""
        error = stderr or ""

        if is_simple or exit_code != 0:
            combined = (output + "\n" + error).strip()
        else:
            combined = output

        err_msg = ""
        if exit_code != 0:
            err_msg = f"exit code {exit_code}"
            if error:
                err_msg += f": {error[:500]}"

        return ToolResult(
            success=exit_code == 0,
            output=combined[:10000],
            error=err_msg,
            exit_code=exit_code,
        )

    except FileNotFoundError:
        return ToolResult(False, "", "bash not found", exit_code=-1)
    except Exception as e:
        return ToolResult(False, "", str(e), exit_code=-1)


def read_file(path: str) -> ToolResult:
    try:
        p = Path(path).resolve()
        if not p.exists():
            return ToolResult(False, "", f"File not found: {path}", exit_code=1)
        if not p.is_file():
            return ToolResult(False, "", f"Not a file: {path}", exit_code=1)
        content = p.read_text(encoding="utf-8", errors="replace")
        return ToolResult(True, content, exit_code=0)
    except PermissionError:
        return ToolResult(False, "", f"Permission denied: {path}", exit_code=1)
    except Exception as e:
        return ToolResult(False, "", str(e), exit_code=1)


def write_file(path: str, content: str) -> ToolResult:
    try:
        p = Path(path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return ToolResult(True, f"Written {len(content)} bytes to {path}", exit_code=0)
    except PermissionError:
        return ToolResult(False, "", f"Permission denied: {path}", exit_code=1)
    except Exception as e:
        return ToolResult(False, "", str(e), exit_code=1)


def edit_file(path: str, old_string: str, new_string: str, replace_all: bool = False) -> ToolResult:
    try:
        p = Path(path).resolve()
        if not p.exists():
            return ToolResult(False, "", f"File not found: {path}", exit_code=1)
        content = p.read_text(encoding="utf-8", errors="replace")
        if old_string not in content:
            return ToolResult(False, "", f"Pattern not found in {path}", exit_code=1)
        if replace_all:
            new_content = content.replace(old_string, new_string)
        else:
            new_content = content.replace(old_string, new_string, 1)
        if new_content == content:
            return ToolResult(False, "", f"No changes made to {path}", exit_code=1)
        p.write_text(new_content, encoding="utf-8")
        diff = list(difflib.unified_diff(
            content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{path}", tofile=f"b/{path}"
        ))
        diff_text = "".join(diff)
        return ToolResult(True, f"Edited {path}\n{diff_text}", exit_code=0)
    except PermissionError:
        return ToolResult(False, "", f"Permission denied: {path}", exit_code=1)
    except Exception as e:
        return ToolResult(False, "", str(e), exit_code=1)


def glob_files(pattern: str, path: str | None = None) -> ToolResult:
    _ensure_workspace()
    try:
        search_path = Path(path or str(TOOL_DIR))
        if not search_path.exists():
            return ToolResult(False, "", f"Directory not found: {path or str(TOOL_DIR)}", exit_code=1)
        matches = sorted(search_path.rglob(pattern))
        result = "\n".join(str(m.relative_to(search_path)) for m in matches) or "No matches found"
        return ToolResult(True, result, exit_code=0)
    except Exception as e:
        return ToolResult(False, "", str(e), exit_code=1)


def list_directory(path: str = ".") -> ToolResult:
    try:
        p = Path(path).resolve()
        if not p.exists():
            return ToolResult(False, "", f"Directory not found: {path}", exit_code=1)
        if not p.is_dir():
            return ToolResult(False, "", f"Not a directory: {path}", exit_code=1)
        entries = []
        for entry in sorted(p.iterdir()):
            suffix = "/" if entry.is_dir() else ""
            entries.append(f"{entry.name}{suffix}")
        return ToolResult(True, "\n".join(entries), exit_code=0)
    except PermissionError:
        return ToolResult(False, "", f"Permission denied: {path}", exit_code=1)
    except Exception as e:
        return ToolResult(False, "", str(e), exit_code=1)


def grep_search(pattern: str, path: str, include: str | None = None) -> ToolResult:
    try:
        p = Path(path).resolve()
        if not p.exists():
            return ToolResult(False, "", f"Path not found: {path}", exit_code=1)
        cmd = f"grep -rn '{pattern}' {shlex.quote(str(p))}"
        if include:
            cmd += f" --include='{include}'"
        return bash_command(cmd)
    except Exception as e:
        return ToolResult(False, "", str(e), exit_code=1)


def file_analysis(path: str) -> ToolResult:
    try:
        p = Path(path).resolve()
        if not p.exists():
            return ToolResult(False, "", f"Path not found: {path}", exit_code=1)
        info = f"Path: {p}\n"
        info += f"Size: {p.stat().st_size} bytes\n"
        info += f"Type: {'directory' if p.is_dir() else 'file'}\n"
        if p.is_file():
            info += f"Lines: {sum(1 for _ in p.open('rb') if _.strip())}\n"
            import stat as stmod
            mode = p.stat().st_mode
            info += f"Permissions: {stmod.filemode(mode)}\n"
        return ToolResult(True, info.strip(), exit_code=0)
    except Exception as e:
        return ToolResult(False, "", str(e), exit_code=1)


AVAILABLE_TOOLS = {
    "bash": {
        "description": "Execute a bash command. Shows real output. Fast-path for simple commands (mkdir, touch, ls, echo, etc).",
        "parameters": {
            "command": "The bash command to execute",
            "workdir": "Working directory (optional)",
            "sandbox": "Run in sandbox (optional, default false)",
        },
    },
    "read_file": {
        "description": "Read the contents of a file at the given path.",
        "parameters": {"path": "Absolute path to the file"},
    },
    "write_file": {
        "description": "Write content to a file. Creates parent directories if needed.",
        "parameters": {
            "path": "Absolute path to the file",
            "content": "Content to write to the file",
        },
    },
    "edit_file": {
        "description": "Edit a file by replacing text. Shows diff of changes. Use replace_all=true to replace all occurrences.",
        "parameters": {
            "path": "Absolute path to the file",
            "old_string": "Text to find and replace",
            "new_string": "Replacement text",
            "replace_all": "Replace all occurrences (default: false)",
        },
    },
    "glob_files": {
        "description": "Find files matching a glob pattern (recursive).",
        "parameters": {
            "pattern": "Glob pattern (e.g. **/*.py)",
            "path": "Root directory (optional, defaults to workspace)",
        },
    },
    "list_directory": {
        "description": "List entries in a directory. Appends / for subdirectories.",
        "parameters": {"path": "Directory path (defaults to current directory)"},
    },
    "grep_search": {
        "description": "Search for a pattern in files using grep.",
        "parameters": {
            "pattern": "Regex pattern to search for",
            "path": "Directory or file to search in",
            "include": "File pattern to include (e.g. *.py)",
        },
    },
    "file_analysis": {
        "description": "Get metadata about a file: size, type, permissions, line count.",
        "parameters": {"path": "Path to the file or directory"},
    },
}

FAST_PATH_TOOLS = {"bash", "read_file", "write_file", "edit_file", "list_directory", "file_analysis"}

def is_fast_path(name: str, kwargs: dict) -> bool:
    if name == "bash":
        cmd = kwargs.get("command", "")
        return _is_simple_command(cmd) or len(cmd) < 50
    if name in FAST_PATH_TOOLS:
        return True
    return False


def execute_tool(name: str, kwargs: dict[str, Any]) -> ToolResult:
    if name == "bash":
        return bash_command(**kwargs)
    elif name == "read_file":
        return read_file(**kwargs)
    elif name == "write_file":
        return write_file(**kwargs)
    elif name == "edit_file":
        return edit_file(**kwargs)
    elif name == "glob_files":
        return glob_files(**kwargs)
    elif name == "list_directory":
        return list_directory(**kwargs)
    elif name == "grep_search":
        return grep_search(**kwargs)
    elif name == "file_analysis":
        return file_analysis(**kwargs)
    else:
        return ToolResult(False, "", f"Unknown tool: {name}", exit_code=-1)
