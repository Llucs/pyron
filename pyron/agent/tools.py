import os
import subprocess
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

_INITIAL_CWD = os.getcwd()


class ToolResult:
    def __init__(self, success: bool, output: str, error: str = ""):
        self.success = success
        self.output = output
        self.error = error

    def to_dict(self) -> dict:
        return {"success": self.success, "output": self.output, "error": self.error}

    def __str__(self) -> str:
        if self.success:
            return self.output[:2000]
        return f"Error: {self.error}\n{self.output[:2000]}"


def bash_command(command: str, workdir: str | None = None) -> ToolResult:
    cwd = workdir or _INITIAL_CWD
    try:
        result = subprocess.run(
            ["bash", "-c", command],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=cwd,
        )
        output = result.stdout + result.stderr
        return ToolResult(
            success=result.returncode == 0,
            output=output[:10000],
            error="" if result.returncode == 0 else f"exit code {result.returncode}",
        )
    except subprocess.TimeoutExpired:
        return ToolResult(False, "", "Command timed out (180s)")
    except Exception as e:
        return ToolResult(False, "", str(e))


def read_file(path: str) -> ToolResult:
    try:
        p = Path(path).resolve()
        if not p.exists():
            return ToolResult(False, "", f"File not found: {path}")
        content = p.read_text()
        return ToolResult(True, content)
    except Exception as e:
        return ToolResult(False, "", str(e))


def write_file(path: str, content: str) -> ToolResult:
    try:
        p = Path(path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return ToolResult(True, f"Written {len(content)} bytes to {path}")
    except Exception as e:
        return ToolResult(False, "", str(e))


def glob_files(pattern: str, path: str | None = None) -> ToolResult:
    try:
        search_path = Path(path or ".").resolve()
        if not search_path.exists():
            return ToolResult(False, "", f"Path not found: {path or '.'}")
        matches = list(search_path.rglob(pattern))
        result = "\n".join(
            str(m.relative_to(search_path)) for m in sorted(matches)
        )
        return ToolResult(True, result or "No matches found")
    except Exception as e:
        return ToolResult(False, "", str(e))


def list_directory(path: str = ".") -> ToolResult:
    try:
        p = Path(path).resolve()
        if not p.exists():
            return ToolResult(False, "", f"Directory not found: {path}")
        entries = []
        for entry in sorted(p.iterdir()):
            suffix = "/" if entry.is_dir() else ""
            entries.append(f"{entry.name}{suffix}")
        return ToolResult(True, "\n".join(entries))
    except Exception as e:
        return ToolResult(False, "", str(e))


def file_search(pattern: str, path: str | None = None, include: str | None = None) -> ToolResult:
    try:
        search_path = Path(path or ".").resolve()
        if not search_path.exists():
            return ToolResult(False, "", f"Path not found: {path or '.'}")
        cmd = f"grep -rn '{pattern}'"
        if include:
            cmd += f" --include='{include}'"
        cmd += f" {search_path}"
        result = subprocess.run(
            ["bash", "-c", cmd],
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout[:10000] or "No matches found"
        return ToolResult(
            success=result.returncode == 0,
            output=output,
            error="" if result.returncode == 0 else "No matches",
        )
    except subprocess.TimeoutExpired:
        return ToolResult(False, "", "Search timed out")
    except Exception as e:
        return ToolResult(False, "", str(e))


def web_fetch(url: str) -> ToolResult:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Pyron/1.0"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read().decode("utf-8", errors="replace")
        return ToolResult(True, content[:10000])
    except Exception as e:
        return ToolResult(False, "", str(e))


def python_repl(code: str) -> ToolResult:
    try:
        namespace = {}
        exec(code, namespace)
        result = namespace.get("result", "Code executed successfully (no result variable)")
        return ToolResult(True, str(result))
    except Exception as e:
        return ToolResult(False, "", str(e))


AVAILABLE_TOOLS = {
    "bash": {
        "description": "Execute a bash command. Returns stdout and stderr.",
        "parameters": {
            "command": "The bash command to execute",
            "workdir": "Working directory (optional)",
        },
    },
    "read_file": {
        "description": "Read the contents of a file.",
        "parameters": {"path": "Absolute path to the file"},
    },
    "write_file": {
        "description": "Write content to a file. Creates parent directories if needed.",
        "parameters": {
            "path": "Absolute path to the file",
            "content": "Content to write",
        },
    },
    "glob_files": {
        "description": "Find files matching a glob pattern (e.g. **/*.py).",
        "parameters": {
            "pattern": "Glob pattern (e.g. **/*.py)",
            "path": "Root directory (optional, default: current)",
        },
    },
    "list_directory": {
        "description": "List entries in a directory.",
        "parameters": {"path": "Directory path (defaults to current)"},
    },
    "file_search": {
        "description": "Search for a regex pattern in files (like grep).",
        "parameters": {
            "pattern": "Regex pattern to search for",
            "path": "Root directory (optional)",
            "include": "File pattern to include (e.g. *.py)",
        },
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


def execute_tool(name: str, kwargs: dict[str, Any]) -> ToolResult:
    tool_map = {
        "bash": bash_command,
        "read_file": read_file,
        "write_file": write_file,
        "glob_files": glob_files,
        "list_directory": list_directory,
        "file_search": file_search,
        "web_fetch": web_fetch,
        "python_repl": python_repl,
    }
    fn = tool_map.get(name)
    if fn:
        return fn(**kwargs)
    return ToolResult(False, "", f"Unknown tool: {name}")
