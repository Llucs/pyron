# Pyron

**Pyron** is an autonomous AI agent that executes tasks using natural language. Powered by the OpenCode API, it plans, executes, and iterates on goals using a suite of tools — all from your terminal.

## Features

- Autonomous task execution with planning and step-by-step reasoning
- Tool use: bash commands, file read/write, glob search, directory listing
- Interactive terminal interface (CLI)
- Optional GUI interface (tkinter)
- Chat mode for direct conversation
- Configurable model and API endpoint

## Installation

```bash
pip install -e .
```

## Usage

### Terminal (Interactive)

```bash
pyron
```

### Single Command

```bash
pyron "Find all Python files and count the lines of code"
```

### GUI Mode

```bash
pyron --gui
```

### Chat Mode

```bash
pyron chat
```

### Commands

| Command       | Description                     |
|---------------|---------------------------------|
| `/help`       | Show help message               |
| `/exit`       | Exit Pyron                      |
| `/config`     | Show current configuration      |
| `/model <m>`  | Change the AI model             |
| `/clear`      | Clear the screen                |
| `/chat`       | Toggle chat mode                |

## Configuration

Configuration is stored at `~/.config/pyron/config.json`.

Default API endpoint: `https://opencode.ai/zen/v1/chat/completions`  
Default model: `deepseek-v4-flash-free`

## Architecture

```
pyron/
├── api/client.py       # OpenCode API client
├── agent/
│   ├── agent.py        # Core agent loop
│   ├── tools.py        # Tool definitions and execution
│   └── planning.py     # Plan creation and management
├── cli/terminal.py     # Terminal interface
└── gui/app.py          # Optional GUI
```

## License

MIT
