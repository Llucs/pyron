import sys
import os
import shutil
import time
import json
from pathlib import Path

from pyron.agent.agent import Agent
from pyron.api.client import ApiClient, Message
from pyron.config import get_api_config, set_api_config


class Style:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"

    FG_CYAN = "\033[96m"
    FG_GREEN = "\033[92m"
    FG_YELLOW = "\033[93m"
    FG_RED = "\033[91m"
    FG_BLUE = "\033[94m"
    FG_MAGENTA = "\033[95m"
    FG_WHITE = "\033[97m"
    FG_GRAY = "\033[90m"
    FG_ORANGE = "\033[38;5;214m"
    FG_PURPLE = "\033[38;5;141m"

    BG_DARK = "\033[48;5;235m"
    BG_DARKER = "\033[48;5;234m"
    BG_BLACK = "\033[40m"

    def fg_rgb(r, g, b):
        return f"\033[38;2;{r};{g};{b}m"

    def bg_rgb(r, g, b):
        return f"\033[48;2;{r};{g};{b}m"


THEME = {
    "primary": Style.fg_rgb(250, 178, 131),
    "secondary": Style.fg_rgb(92, 156, 245),
    "accent": Style.fg_rgb(157, 124, 216),
    "success": Style.fg_rgb(127, 216, 143),
    "warning": Style.fg_rgb(245, 167, 66),
    "error": Style.fg_rgb(224, 108, 117),
    "info": Style.fg_rgb(86, 182, 194),
    "text": Style.fg_rgb(238, 238, 238),
    "text_muted": Style.fg_rgb(128, 128, 128),
    "bg_panel": Style.bg_rgb(20, 20, 20),
    "bg_element": Style.bg_rgb(30, 30, 30),
    "border": Style.fg_rgb(72, 72, 72),
}


PYRON_LOGO = f"""
{THEME["primary"]}{Style.BOLD}
   ██████╗ ██╗   ██╗██████╗  ██████╗ ███╗   ██╗
   ██╔══██╗╚██╗ ██╔╝██╔══██╗██╔═══██╗████╗  ██║
   ██████╔╝ ╚████╔╝ ██████╔╝██║   ██║██╔██╗ ██║
   ██╔═══╝   ╚██╔╝  ██╔══██╗██║   ██║██║╚██╗██║
   ██║        ██║   ██║  ██║╚██████╔╝██║ ╚████║
   ╚═╝        ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝
{Style.RESET}{THEME["accent"]}      Autonomous AI Agent — v1.1.0{Style.RESET}
"""


def c(text, color=None, bold=False, dim=False, italic=False, reset=True):
    parts = []
    if color:
        parts.append(color)
    if bold:
        parts.append(Style.BOLD)
    if dim:
        parts.append(Style.DIM)
    if italic:
        parts.append(Style.ITALIC)
    parts.append(str(text))
    if reset:
        parts.append(Style.RESET)
    return "".join(parts)


def print_line(char="─", color=None):
    w = shutil.get_terminal_size().columns
    if color:
        sys.stdout.write(f"{color}{char * w}{Style.RESET}\n")
    else:
        sys.stdout.write(f"{THEME['border']}{char * w}{Style.RESET}\n")
    sys.stdout.flush()


def print_header():
    w = shutil.get_terminal_size().columns
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

    for line in PYRON_LOGO.split("\n"):
        if line.strip():
            sys.stdout.write(f"  {line}\n")
    sys.stdout.flush()

    cfg = get_api_config()
    print_line()
    sys.stdout.write(f"  {c('Model:', THEME['text_muted'])} {c(cfg['model'], THEME['secondary'])}")
    sys.stdout.write(f"  {c('API:', THEME['text_muted'])} {c(cfg['base_url'][:50], THEME['text'], dim=True)}")
    sys.stdout.write(f"  {c('v1.1.0', THEME['accent'])}\n")
    print_line()
    sys.stdout.write("\n")
    sys.stdout.flush()


def print_help():
    sys.stdout.write(f"\n  {c('Commands', THEME['primary'], bold=True)}\n")
    sys.stdout.write(f"    {c('/exit', THEME['secondary'])}       {c('- Exit Pyron', THEME['text_muted'])}\n")
    sys.stdout.write(f"    {c('/help', THEME['secondary'])}       {c('- Show this help', THEME['text_muted'])}\n")
    sys.stdout.write(f"    {c('/config', THEME['secondary'])}     {c('- Show configuration', THEME['text_muted'])}\n")
    sys.stdout.write(f"    {c('/model', THEME['secondary'])} <m>  {c('- Change model', THEME['text_muted'])}\n")
    sys.stdout.write(f"    {c('/clear', THEME['secondary'])}      {c('- Clear screen', THEME['text_muted'])}\n")
    sys.stdout.write(f"    {c('/chat', THEME['secondary'])}       {c('- Chat mode (no tools)', THEME['text_muted'])}\n")
    sys.stdout.write(f"\n  {c('Usage', THEME['primary'], bold=True)}\n")
    sys.stdout.write(f"    {c('Enter a goal for Pyron to execute autonomously.', THEME['text_muted'])}\n")
    sys.stdout.write(f"    {c('Simple tasks use fast-path execution automatically.', THEME['text_muted'])}\n\n")


def print_tool_exec(name, args, output, success, duration):
    status = c("OK", THEME["success"]) if success else c("FAIL", THEME["error"])
    sys.stdout.write(f"  {c('⚡', THEME['warning'])} {c(name.upper(), THEME['primary'], bold=True)} {status}\n")
    if args:
        args_str = ", ".join(f"{k}={v}" for k, v in args.items() if k != "content")
        if args_str:
            sys.stdout.write(f"    {c(args_str, THEME['text_muted'])}\n")
    if output:
        trimmed = output[:500].strip()
        if trimmed:
            for line in trimmed.split("\n")[:5]:
                sys.stdout.write(f"    {c('▎', THEME['border'])} {c(line, THEME['text'], dim=True)}\n")
            if len(trimmed) < len(output.strip()):
                sys.stdout.write(f"    {c('... (truncated)', THEME['text_muted'])}\n")
    if duration > 0.1:
        sys.stdout.write(f"    {c(f'({duration:.1f}s)', THEME['text_muted'])}\n")
    sys.stdout.flush()


def chat_mode():
    print_header()
    sys.stdout.write(f"  {c('Chat mode enabled.', THEME['info'])} {c('/back to return.', THEME['text_muted'])}\n\n")
    sys.stdout.flush()
    client = ApiClient()
    history = [Message("system", "You are Pyron, an autonomous AI assistant with file system access.")]

    while True:
        try:
            sys.stdout.write(f"  {c('💬', THEME['secondary'])} {c('chat> ', THEME['primary'], bold=True)}")
            sys.stdout.flush()
            user_input = input().strip()
        except (EOFError, KeyboardInterrupt):
            sys.stdout.write("\n")
            break

        if not user_input:
            continue
        if user_input == "/back":
            break

        history.append(Message("user", user_input))
        sys.stdout.write(f"\n  {c('Pyron is thinking...', THEME['text_muted'], italic=True)}\n")
        sys.stdout.flush()
        start = time.time()
        response = client.complete(history)
        elapsed = time.time() - start

        sys.stdout.write(f"\n  {c(response.content, THEME['text'])}\n")
        if response.usage:
            sys.stdout.write(f"\n  {c(f'({elapsed:.1f}s · {response.usage.total_tokens} tokens)', THEME['text_muted'])}\n")
        sys.stdout.write("\n")
        history.append(Message("assistant", response.content))
        sys.stdout.flush()


def interactive_loop():
    print_header()
    print_help()

    while True:
        try:
            sys.stdout.write(f"  {c('▸', THEME['primary'], bold=True)} {c('pyron', THEME['accent'])} {c('~ ', THEME['text_muted'])}")
            sys.stdout.flush()
            user_input = input().strip()
        except (EOFError, KeyboardInterrupt):
            sys.stdout.write(f"\n  {c('Exiting Pyron.', THEME['warning'])}\n")
            break

        if not user_input:
            continue

        if user_input == "/exit":
            sys.stdout.write(f"  {c('Exiting Pyron.', THEME['warning'])}\n")
            sys.stdout.flush()
            break

        if user_input == "/help":
            print_help()
            continue

        if user_input == "/config":
            cfg = get_api_config()
            sys.stdout.write(f"\n  {c('Configuration', THEME['primary'], bold=True)}\n")
            for k, v in cfg.items():
                sys.stdout.write(f"    {c(f'{k}:', THEME['text_muted'])} {c(str(v), THEME['text'])}\n")
            sys.stdout.write("\n")
            sys.stdout.flush()
            continue

        if user_input.startswith("/model "):
            model = user_input[7:].strip()
            set_api_config(model=model)
            sys.stdout.write(f"  {c('✓', THEME['success'])} {c('Model set to:', THEME['text'])} {c(model, THEME['secondary'], bold=True)}\n")
            sys.stdout.flush()
            continue

        if user_input == "/clear":
            print_header()
            continue

        if user_input == "/chat":
            chat_mode()
            print_header()
            continue

        print_line("━", THEME["bg_panel"])
        sys.stdout.write(f"  {c('⚡ Initializing execution...', THEME['info'], italic=True)}\n")
        sys.stdout.flush()

        start = time.time()
        agent = Agent()
        result = agent.run(user_input)
        elapsed = time.time() - start

        sys.stdout.write(f"\n  {c('■', THEME['success'])} {c('Result', THEME['success'], bold=True)}\n")
        if result:
            for line in result.split("\n"):
                if line.strip():
                    sys.stdout.write(f"    {c('▎', THEME['border'])} {c(line.strip(), THEME['text'])}\n")
        sys.stdout.write(f"\n  {c(f'⏱ {elapsed:.1f}s', THEME['text_muted'])}\n")
        print_line("━", THEME["bg_panel"])
        sys.stdout.write("\n")
        sys.stdout.flush()


def main():
    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        print_header()
        print_help()
        return

    if "--model" in args:
        idx = args.index("--model")
        if idx + 1 < len(args):
            set_api_config(model=args[idx + 1])
            sys.stdout.write(f"  {c('✓ Model set to:', THEME['success'])} {c(args[idx + 1], THEME['secondary'])}\n")
            sys.stdout.flush()
            return

    if args and args[0] == "chat":
        chat_mode()
        return

    if args:
        goal = " ".join(args)
        sys.stdout.write(f"  {c('⚡', THEME['warning'])} {c('Pyron:', THEME['primary'], bold=True)} {c(goal, THEME['text'])}\n")
        sys.stdout.flush()
        start = time.time()
        agent = Agent()
        result = agent.run(goal)
        elapsed = time.time() - start
        sys.stdout.write(f"\n  {c('■ Result', THEME['success'], bold=True)}\n")
        if result:
            for line in result.split("\n"):
                if line.strip():
                    sys.stdout.write(f"    {c('▎', THEME['border'])} {c(line.strip(), THEME['text'])}\n")
        sys.stdout.write(f"  {c(f'⏱ {elapsed:.1f}s', THEME['text_muted'])}\n")
        sys.stdout.flush()
        return

    interactive_loop()


if __name__ == "__main__":
    main()
