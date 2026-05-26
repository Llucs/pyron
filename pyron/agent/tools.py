import os
import subprocess
import json
from pathlib import Path
from typing import Any


TOOL_DIR = Path.home() / ".pyron" / "workspace"


def _ensure_workspace():
    TOOL_DIR.mkdir(parents=True, exist_ok=True)


class ToolResult:
    def __init__(self, success: bool, output: str, error: str = ""):
        self.success = success
        self.output = output
        self.error = error

    def to_dict(self) -> dict:
        return {"success": self.success, "output": self.output, "error": self.error}


def bash_command(command: str, workdir: str | None = None) -> ToolResult:
    _ensure_workspace()
    cwd = workdir or str(TOOL_DIR)
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
    _ensure_workspace()
    try:
        search_path = Path(path or str(TOOL_DIR))
        matches = list(search_path.rglob(pattern))
        result = "\n".join(str(m.relative_to(search_path)) for m in matches)
        return ToolResult(True, result or "No matches found")
    except Exception as e:
        return ToolResult(False, "", str(e))


def list_directory(path: str = ".") -> ToolResult:
    try:
        p = Path(path).resolve()
        if not p.exists():
            return ToolResult(False, "", f"Directory not found: {path}")
        entries = []
        for entry in p.iterdir():
            suffix = "/" if entry.is_dir() else ""
            entries.append(f"{entry.name}{suffix}")
        return ToolResult(True, "\n".join(entries))
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
        "description": "Find files matching a glob pattern.",
        "parameters": {
            "pattern": "Glob pattern (e.g. **/*.py)",
            "path": "Root directory (optional)",
        },
    },
    "list_directory": {
        "description": "List entries in a directory.",
        "parameters": {"path": "Directory path (defaults to current)"},
    },
}


def execute_tool(name: str, kwargs: dict[str, Any]) -> ToolResult:
    if name == "bash":
        return bash_command(**kwargs)
    elif name == "read_file":
        return read_file(**kwargs)
    elif name == "write_file":
        return write_file(**kwargs)
    elif name == "glob_files":
        return glob_files(**kwargs)
    elif name == "list_directory":
        return list_directory(**kwargs)
    else:
        return ToolResult(False, "", f"Unknown tool: {name}")
