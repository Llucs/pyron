import sys
import os
import shutil

from pyron.agent.agent import Agent
from pyron.api.client import ApiClient, Message
from pyron.config import get_api_config, set_api_config
from pyron.memory_manager import MemoryManager, SYSTEM_MASTER_PROMPT


class Style:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"

    @staticmethod
    def fg(r, g, b):
        return f"\033[38;2;{r};{g};{b}m"

    @staticmethod
    def bg(r, g, b):
        return f"\033[48;2;{r};{g};{b}m"


P = Style.fg(250, 178, 131)
S = Style.fg(92, 156, 245)
A = Style.fg(157, 124, 216)
G = Style.fg(127, 216, 143)
W = Style.fg(245, 167, 66)
E = Style.fg(224, 108, 117)
I = Style.fg(86, 182, 194)
T = Style.fg(238, 238, 238)
M = Style.fg(128, 128, 128)
B = Style.fg(72, 72, 72)


def c(text, color=None, bold=False, dim=False, italic=False):
    parts = []
    if bold:
        parts.append(Style.BOLD)
    if dim:
        parts.append(Style.DIM)
    if italic:
        parts.append(Style.ITALIC)
    if color:
        parts.append(color)
    parts.append(str(text))
    parts.append(Style.RESET)
    return "".join(parts)


LOGO = f"""
{P}{Style.BOLD}
   ██████╗ ██╗   ██╗██████╗  ██████╗ ███╗   ██╗
   ██╔══██╗╚██╗ ██╔╝██╔══██╗██╔═══██╗████╗  ██║
   ██████╔╝ ╚████╔╝ ██████╔╝██║   ██║██╔██╗ ██║
   ██╔═══╝   ╚██╔╝  ██╔══██╗██║   ██║██║╚██╗██║
   ██║        ██║   ██║  ██║╚██████╔╝██║ ╚████║
   ╚═╝        ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝
{Style.RESET}{A}      Autonomous AI Agent \u2014 v2.2.0{Style.RESET}
"""


def print_line(char="\u2500"):
    w = shutil.get_terminal_size().columns
    sys.stdout.write(f"{B}{char * w}{Style.RESET}\n")
    sys.stdout.flush()


def print_header():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()
    for line in LOGO.split("\n"):
        if line.strip():
            sys.stdout.write(f"  {line}\n")
    sys.stdout.flush()
    cfg = get_api_config()
    print_line()
    sys.stdout.write(f"  {c('Model:', M)} {c(cfg['model'], S)}  {c('API:', M)} {c(cfg['base_url'][:50], M, dim=True)}  {c('v2.2.0', A)}\n")
    print_line()
    sys.stdout.write("\n")
    sys.stdout.flush()


def print_help():
    sys.stdout.write(f"\n  {c('Commands', P, bold=True)}\n")
    sys.stdout.write(f"    {c('/exit', S)}     {c('- Exit Pyron', M)}\n")
    sys.stdout.write(f"    {c('/help', S)}     {c('- Show this help', M)}\n")
    sys.stdout.write(f"    {c('/version', S)}  {c('- Show version', M)}\n")
    sys.stdout.write(f"    {c('/config', S)}   {c('- Show configuration', M)}\n")
    sys.stdout.write(f"    {c('/model', S)} <m>{c('- Change model', M)}\n")
    sys.stdout.write(f"    {c('/clear', S)}    {c('- Clear screen', M)}\n")
    sys.stdout.write(f"    {c('/chat', S)}     {c('- Toggle chat mode', M)}\n")
    sys.stdout.write(f"    {c('/memory', S)}   {c('- Memory stats', M)}\n")
    sys.stdout.write(f"    {c('/plan', S)} <g> {c('- Execute goal', M)}\n")
    sys.stdout.write(f"    {c('/forget', S)}   {c('- Prune memories', M)}\n")
    sys.stdout.write(f"\n  {c('Enter any task \u2014 Pyron plans and executes autonomously.', M)}\n\n")


def _show_memory_stats(memory: MemoryManager):
    stats = memory.get_stats()
    for k, v in [("working items", stats["working_items"]), ("working tokens", stats["working_tokens"]), ("vector store", stats["vector_items"]), ("kg entities", stats["kg_entities"]), ("kg relations", stats["kg_relations"]), ("compressions", stats["compressions"]), ("interactions", stats["interactions"])]:
        sys.stdout.write(f"  {c(k, M)}: {c(str(v), T)}\n")
    levels = []
    if stats["level1_summary"]:
        levels.append("L1")
    if stats["level2_summary"]:
        levels.append("L2")
    if stats["level3_summary"]:
        levels.append("L3")
    if levels:
        sys.stdout.write(f"  {c('summaries', M)}: {c(', '.join(levels), S)}\n")
    sys.stdout.write("\n")
    sys.stdout.flush()


def interactive_loop():
    print_header()
    print_help()

    agent = Agent(log_fn=lambda x: sys.stdout.write(x + "\n"), status_fn=lambda x: (sys.stdout.write(x), sys.stdout.flush()))
    chat_history = [Message("system", SYSTEM_MASTER_PROMPT)]
    chat_only = False

    while True:
        try:
            sys.stdout.write(f"  {c('\u25b8', P, bold=True)} {c('pyron', A)} {c('~', M)} ")
            sys.stdout.flush()
            inp = input().strip()
        except (EOFError, KeyboardInterrupt):
            sys.stdout.write(f"\n  {c('Exiting Pyron.', W)}\n")
            sys.stdout.flush()
            break

        if not inp:
            continue

        if inp == "/exit":
            sys.stdout.write(f"  {c('Exiting Pyron.', W)}\n")
            sys.stdout.flush()
            break

        if inp == "/help":
            print_help()
            continue

        if inp == "/version":
            from pyron.__init__ import __version__
            sys.stdout.write(f"  {c('Pyron', P, bold=True)} {c(__version__, A)}\n")
            sys.stdout.flush()
            continue

        if inp == "/config":
            sys.stdout.write(f"\n  {c('Configuration', P, bold=True)}\n")
            for k, v in get_api_config().items():
                sys.stdout.write(f"    {c(k, M)}: {c(str(v), T)}\n")
            sys.stdout.write("\n")
            sys.stdout.flush()
            continue

        if inp.startswith("/model "):
            m = inp[7:].strip()
            set_api_config(model=m)
            sys.stdout.write(f"  {c('\u2713', G)} {c('Model:', T)} {c(m, S, bold=True)}\n")
            sys.stdout.flush()
            continue

        if inp == "/clear":
            print_header()
            continue

        if inp == "/chat":
            chat_only = not chat_only
            sys.stdout.write(f"  {c('Chat:', M)} {c('ON' if chat_only else 'OFF', G if chat_only else E)}\n")
            sys.stdout.flush()
            continue

        if inp == "/memory":
            _show_memory_stats(agent.memory)
            continue

        if inp == "/forget":
            n = agent.memory.apply_forgetting(threshold=0.1)
            sys.stdout.write(f"  {c('Pruned', G)} {c(f'{n} memories', M)}\n")
            sys.stdout.flush()
            continue

        if inp.startswith("/plan "):
            goal = inp[6:].strip()
            if not goal:
                sys.stdout.write(f"  {c('Specify a goal.', W)}\n")
                sys.stdout.flush()
                continue
            agent = Agent(log_fn=lambda x: sys.stdout.write(x + "\n"), status_fn=lambda x: (sys.stdout.write(x), sys.stdout.flush()))

        if chat_only:
            chat_history.append(Message("user", inp))
            try:
                sys.stdout.write(f"  {c('Pyron thinking...', M, italic=True)}\n")
                sys.stdout.flush()
                r = agent.client.complete(chat_history)
                sys.stdout.write(f"\n  {c(r.content, T)}\n\n")
                chat_history.append(Message("assistant", r.content))
            except Exception as e:
                sys.stdout.write(f"\n  {c(str(e), E)}\n\n")
            sys.stdout.flush()
            continue

        agent = Agent(log_fn=lambda x: sys.stdout.write(x + "\n"), status_fn=lambda x: (sys.stdout.write(x), sys.stdout.flush()))
        try:
            agent.run(inp)
            sys.stdout.write(f"\n")
            sys.stdout.flush()
        except Exception as e:
            sys.stdout.write(f"\n  {c(str(e), E)}\n\n")
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
            sys.stdout.write(f"  {c('\u2713', G)} {c('Model:', T)} {c(args[idx + 1], S)}\n")
            sys.stdout.flush()
            return

    if args:
        goal = " ".join(args)
        sys.stdout.write(f"  {c('\u26a1', W)} {c('Pyron:', P, bold=True)} {c(goal, T)}\n")
        sys.stdout.flush()
        agent = Agent(log_fn=lambda x: sys.stdout.write(x + "\n"), status_fn=lambda x: (sys.stdout.write(x), sys.stdout.flush()))
        try:
            agent.run(goal)
            sys.stdout.write(f"\n")
        except Exception as e:
            sys.stdout.write(f"\n  {c(str(e), E)}\n\n")
        sys.stdout.flush()
        return

    interactive_loop()


if __name__ == "__main__":
    main()
