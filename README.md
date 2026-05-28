# Pyron

**Pyron** is an autonomous AI agent with **hierarchical memory** that provides an effective context of ~1 million tokens. Powered by the OpenCode API, it plans, executes, and iterates on goals using a suite of tools — all from your terminal.

Unlike standard AI agents limited to their model's native context window (e.g., 200K tokens), Pyron uses a layered memory architecture to **retain, compress, and retrieve** information across sessions, enabling long-running autonomous operation.

## Features

- **Hierarchical Memory System** — 4 layers: Working Memory, Vector Store (semantic search), Hierarchical Summaries (3 levels), and Knowledge Graph (entity-relation store)
- **Automatic Context Compression** — Monitors token usage and compresses when exceeding 140K tokens using Chain-of-Density/Map-Reduce
- **Periodic Reflection** — Self-analysis every 8-12 interactions to adjust priorities and reinforce learning
- **Forgetting Curve** — Ebbinghaus-inspired decay removes low-importance information gradually
- **Autonomous Task Execution** — Planning, step-by-step reasoning, and tool use
- **8 Built-in Tools** — bash, file read/write, glob, directory listing, file search (grep), web fetch, Python REPL
- **Interactive Terminal (CLI)** with memory inspection commands
- **Optional GUI** (tkinter) with memory layer visualization
- **Chat Mode** for direct conversation with memory context

## Installation

```bash
pip install -e .
```

No external dependencies required (uses Python standard library).

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
| `/memory`     | Show memory layer statistics    |
| `/forget`     | Prune old/unimportant memories  |

## Memory Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Working Memory (180K tokens)            │
│  Immediate context used in the main prompt              │
├─────────────────────────────────────────────────────────┤
│              Short-Term Memory (Vector Store)            │
│  All recent interactions stored as embeded chunks       │
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
