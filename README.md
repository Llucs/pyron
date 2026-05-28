# Pyron

**Pyron** is an autonomous AI agent with **hierarchical memory** that provides an effective context of ~1 million tokens. Powered by the OpenCode API, it plans, executes, and iterates on goals using a suite of tools — all from your terminal.

Unlike standard AI agents limited to their model's native context window (e.g., 200K tokens), Pyron uses a layered memory architecture to **retain, compress, and retrieve** information across sessions, enabling long-running autonomous operation.

Pyron works like a **free terminal** — type any task or question, and it plans, executes tools, and returns results. Just like OpenCode, Openhands, or Claude Code.

## Features

- **Hierarchical Memory System** — 4 layers: Working Memory, Vector Store (semantic search), Hierarchical Summaries (3 levels), and Knowledge Graph (entity-relation store)
- **Automatic Context Compression** — Monitors token usage and compresses when exceeding 140K tokens
- **Periodic Reflection** — Self-analysis every 8-12 interactions to adjust priorities and reinforce learning
- **Forgetting Curve** — Ebbinghaus-inspired decay removes low-importance information gradually
- **Autonomous Task Execution** — Planning, step-by-step reasoning, and tool use
- **8 Built-in Tools** — bash, file read/write, glob, directory listing, grep, web fetch, Python REPL
- **Interactive Terminal** — free-form: just type what you want done
- **Optional GUI** (tkinter) with memory layer visualization
- **Chat Mode** for pure conversation (no tool execution)

## Installation

```bash
pip install -e .
```

No external dependencies required (uses Python standard library).

## Usage

### Free Terminal (Interactive)

Just type any task. Pyron plans and executes with full tool access.

```bash
pyron
```

```
pyron> Find all Python files and count the lines of code
pyron> Create a REST API with Flask in ./api/
pyron> Search for TODO comments across the project
```

### Single Command

```bash
pyron "Find all Python files and count the lines of code"
```

### GUI Mode

```bash
pyron --gui
```

### Commands

| Command       | Description                                     |
|---------------|-------------------------------------------------|
| `/exit`       | Exit Pyron                                      |
| `/help`       | Show this help message                          |
| `/config`     | Show current configuration                      |
| `/model <m>`  | Change the AI model                             |
| `/clear`      | Clear the screen                                |
| `/chat`       | Toggle pure chat mode (no tool execution)       |
| `/plan <goal>`| Force explicit plan-execute mode for a goal     |
| `/memory`     | Show memory layer statistics                    |
| `/forget`     | Prune old/unimportant memories                  |

### Examples

```bash
# Start interactive mode
pyron

# Inside Pyron, type anything:
pyron> Search for all Python files with "import os"
pyron> Read the first 20 lines of src/main.py
pyron> Create a new directory structure for a Django project
pyron> /plan Build a complete Flask CRUD API with SQLite
pyron> /chat   # Switch to pure conversation mode
chat> What do you think about the code architecture?
```

## Memory Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Working Memory (180K tokens)            │
│  Immediate context used in the main prompt              │
├─────────────────────────────────────────────────────────┤
│              Short-Term Memory (Vector Store)            │
│  All recent interactions stored as embedded chunks      │
│  Retrieved via hybrid search (semantic + recency + imp) │
├─────────────────────────────────────────────────────────┤
│           Mid-Term Memory (Hierarchical Summaries)       │
│  Level 1: Detailed summary of last 100-150K tokens      │
│  Level 2: Medium-term summary (recent days)             │
│  Level 3: Strategic overview of all relevant history    │
├─────────────────────────────────────────────────────────┤
│              Long-Term Memory (Knowledge Graph)          │
│  Entities, objectives, facts, decisions, and relations  │
│  Precise and efficient retrieval of permanent knowledge │
└─────────────────────────────────────────────────────────┘
```

### Agent Loop

```
Retrieve → Compress (if needed) → Plan → Act → Observe → Save → Reflect
```

## Configuration

Configuration is stored at `~/.config/pyron/config.json`.

Default API endpoint: `https://opencode.ai/zen/v1/chat/completions`  
Default model: `deepseek-v4-flash-free`

## Architecture

```
pyron/
├── __init__.py            # Version info
├── __main__.py            # Entry point
├── config.py              # Configuration management
├── memory_manager.py      # Hierarchical memory system
├── api/client.py          # OpenCode API client
├── agent/
│   ├── agent.py           # Core agent loop with memory integration
│   ├── tools.py           # Tool definitions and execution
│   └── planning.py        # Plan creation and management
├── cli/terminal.py        # Terminal interface
└── gui/app.py             # Optional GUI with memory visualization
```

## License

MIT
