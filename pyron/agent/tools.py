import os
import shlex
import signal
import subprocess
import json
import difflib
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

_INITIAL_CWD = os.getcwd()

SIMPLE_COMMANDS = {"mkdir", "touch", "ls", "echo", "cat", "cp", "mv", "rm", "pwd", "whoami", "date", "which", "printf", "dirname", "basename", "realpath", "readlink"}
FAST_PATH_TIMEOUT = 10
NORMAL_TIMEOUT = 60
LONG_TIMEOUT = 300


class ToolResult:
    def __init__(self, success: bool, output: str, error: str = "", exit_code: int = 0):
        self.success = success
        self.output = output
        self.error = error
        self.exit_code = exit_code

    def to_dict(self) -> dict:
        return {"success": self.success, "output": self.output, "error": self.error, "exit_code": self.exit_code}

    def __str__(self) -> str:
        if self.success:
            return self.output[:2000]
        return f"Error: {self.error}\n{self.output[:2000]}"

    @property
    def is_real_failure(self) -> bool:
        if self.exit_code != 0:
            return True
        if self.error and ("timed out" in self.error.lower() or "killed" in self.error.lower() or "permission denied" in self.error.lower()):
            return True
        if self.error and "not found" in self.error.lower() and "pyron" not in self.error.lower():
            return True
        return False


def _is_simple_command(command: str) -> bool:
    cmd = command.strip().split()[0] if command.strip() else ""
    return cmd in SIMPLE_COMMANDS


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
    cwd = workdir or _INITIAL_CWD
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

        return ToolResult(success=exit_code == 0, output=combined[:10000], error=err_msg, exit_code=exit_code)

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
        new_content = content.replace(old_string, new_string) if replace_all else content.replace(old_string, new_string, 1)
        if new_content == content:
            return ToolResult(False, "", f"No changes made to {path}", exit_code=1)
        p.write_text(new_content, encoding="utf-8")
        diff = list(difflib.unified_diff(
            content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{path}", tofile=f"b/{path}"
        ))
        return ToolResult(True, f"Edited {path}\n{''.join(diff)}", exit_code=0)
    except PermissionError:
        return ToolResult(False, "", f"Permission denied: {path}", exit_code=1)
    except Exception as e:
        return ToolResult(False, "", str(e), exit_code=1)


def glob_files(pattern: str, path: str | None = None) -> ToolResult:
    try:
        search_path = Path(path or ".").resolve()
        if not search_path.exists():
            return ToolResult(False, "", f"Path not found: {path or '.'}", exit_code=1)
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
        entries = [f"{e.name}/" if e.is_dir() else e.name for e in sorted(p.iterdir())]
        return ToolResult(True, "\n".join(entries), exit_code=0)
    except PermissionError:
        return ToolResult(False, "", f"Permission denied: {path}", exit_code=1)
    except Exception as e:
        return ToolResult(False, "", str(e), exit_code=1)


def file_search(pattern: str, path: str | None = None, include: str | None = None) -> ToolResult:
    try:
        search_path = Path(path or ".").resolve()
        if not search_path.exists():
            return ToolResult(False, "", f"Path not found: {path or '.'}", exit_code=1)
        cmd = f"grep -rn '{pattern}'"
        if include:
            cmd += f" --include='{include}'"
        cmd += f" {shlex.quote(str(search_path))}"
        return bash_command(cmd)
    except Exception as e:
        return ToolResult(False, "", str(e), exit_code=1)


def web_fetch(url: str) -> ToolResult:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Pyron/2.1"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read().decode("utf-8", errors="replace")
        return ToolResult(True, content[:10000], exit_code=0)
    except Exception as e:
        return ToolResult(False, "", str(e), exit_code=1)


def python_repl(code: str) -> ToolResult:
    try:
        namespace = {}
        exec(code, namespace)
        result = namespace.get("result", "Code executed successfully (no result variable)")
        return ToolResult(True, str(result), exit_code=0)
    except Exception as e:
        return ToolResult(False, "", str(e), exit_code=1)


def file_analysis(path: str) -> ToolResult:
    try:
        p = Path(path).resolve()
        if not p.exists():
            return ToolResult(False, "", f"Path not found: {path}", exit_code=1)
        import stat as stmod
        mode = p.stat().st_mode
        info = f"Path: {p}\nSize: {p.stat().st_size} bytes\nType: {'directory' if p.is_dir() else 'file'}"
        if p.is_file():
            info += f"\nLines: {sum(1 for _ in p.open('rb') if _.strip())}"
        info += f"\nPermissions: {stmod.filemode(mode)}"
        return ToolResult(True, info, exit_code=0)
    except Exception as e:
        return ToolResult(False, "", str(e), exit_code=1)


AVAILABLE_TOOLS = {
    "bash": {
        "description": "Execute a bash command. Fast-path for simple commands (mkdir, touch, ls, echo).",
        "parameters": {"command": "The bash command to execute", "workdir": "Working directory (optional)", "sandbox": "Run in sandbox (optional)"},
    },
    "read_file": {
        "description": "Read the contents of a file.",
        "parameters": {"path": "Absolute path to the file"},
    },
    "write_file": {
        "description": "Write content to a file. Creates parent directories if needed.",
        "parameters": {"path": "Absolute path to the file", "content": "Content to write"},
    },
    "edit_file": {
        "description": "Edit a file by replacing text. Shows diff. Use replace_all=true for all occurrences.",
        "parameters": {"path": "Absolute path to the file", "old_string": "Text to find", "new_string": "Replacement text", "replace_all": "Replace all occurrences (optional)"},
    },
    "glob_files": {
        "description": "Find files matching a glob pattern (e.g. **/*.py).",
        "parameters": {"pattern": "Glob pattern", "path": "Root directory (optional)"},
    },
    "list_directory": {
        "description": "List entries in a directory.",
        "parameters": {"path": "Directory path (defaults to current)"},
    },
    "file_search": {
        "description": "Search for a regex pattern in files (like grep).",
        "parameters": {"pattern": "Regex pattern", "path": "Root directory (optional)", "include": "File pattern to include (e.g. *.py)"},
    },
    "file_analysis": {
        "description": "Get metadata about a file: size, type, permissions, line count.",
        "parameters": {"path": "Path to the file or directory"},
    },
    "web_fetch": {
        "description": "Fetch and read the contents of a URL.",
        "parameters": {"url": "The URL to fetch"},
    },
    "python_repl": {
        "description": "Execute Python code in a REPL sandbox. Use 'result' variable for output.",
        "parameters": {"code": "Python code to execute"},
    },
}

FAST_PATH_TOOLS = {"bash", "read_file", "write_file", "edit_file", "list_directory", "file_analysis"}


def is_fast_path(name: str, kwargs: dict) -> bool:
    if name == "bash":
        return _is_simple_command(kwargs.get("command", "")) or len(kwargs.get("command", "")) < 50
    return name in FAST_PATH_TOOLS


def execute_tool(name: str, kwargs: dict[str, Any]) -> ToolResult:
    tool_map = {
        "bash": bash_command,
        "read_file": read_file,
        "write_file": write_file,
        "edit_file": edit_file,
        "glob_files": glob_files,
        "list_directory": list_directory,
        "file_search": file_search,
        "file_analysis": file_analysis,
        "web_fetch": web_fetch,
        "python_repl": python_repl,
    }
    fn = tool_map.get(name)
    if fn:
        return fn(**kwargs)
    return ToolResult(False, "", f"Unknown tool: {name}", exit_code=-1)
