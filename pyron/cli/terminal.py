import sys

from pyron.agent.agent import Agent
from pyron.api.client import ApiClient, Message
from pyron.config import get_api_config, set_api_config
from pyron.memory_manager import MemoryManager, SYSTEM_MASTER_PROMPT


def _color(s, code):
    return f"\033[{code}m{s}\033[0m"


def _dim(s):
    return _color(s, 2)


def _green(s):
    return _color(s, 32)


def _red(s):
    return _color(s, 31)


def _blue(s):
    return _color(s, 34)


def _yellow(s):
    return _color(s, 33)


def _cyan(s):
    return _color(s, 36)


def _bold(s):
    return _color(s, 1)


def print_help():
    print(f"  {_bold('/commands')}")
    print(f"    {_bold('/exit')}          exit")
    print(f"    {_bold('/help')}          this help")
    print(f"    {_bold('/version')}       show version")
    print(f"    {_bold('/config')}        show config")
    print(f"    {_bold('/model')} <name>  change model")
    print(f"    {_bold('/clear')}         clear screen")
    print(f"    {_bold('/chat')}          toggle chat mode")
    print(f"    {_bold('/plan')} <goal>   execute plan")
    print(f"    {_bold('/memory')}        memory stats")
    print(f"    {_bold('/forget')}        prune memories")
    print()
    print(f"  {_dim('type any task — pyron plans and executes')}")


def _show_memory_stats(memory: MemoryManager):
    stats = memory.get_stats()
    for k, v in [
        ("working items", stats["working_items"]),
        ("working tokens", stats["working_tokens"]),
        ("vector store", stats["vector_items"]),
        ("kg entities", stats["kg_entities"]),
        ("kg relations", stats["kg_relations"]),
        ("compressions", stats["compressions"]),
        ("interactions", stats["interactions"]),
    ]:
        print(f"  {_dim(k)}: {v}")
    levels = []
    if stats["level1_summary"]:
        levels.append("L1")
    if stats["level2_summary"]:
        levels.append("L2")
    if stats["level3_summary"]:
        levels.append("L3")
    if levels:
        print(f"  {_dim('summaries')}: {', '.join(levels)}")
    print()


def interactive_loop():
    print_help()

    agent = Agent(
        log_fn=lambda x: print(x, flush=True),
        status_fn=lambda x: print(x, end="", flush=True),
    )
    chat_history = [Message("system", SYSTEM_MASTER_PROMPT)]
    chat_only = False
    cfg = get_api_config()

    while True:
        try:
            prompt = f"\r\033[K{_cyan('pyron')}> "
            inp = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not inp:
            continue

        if inp == "/exit":
            break

        if inp == "/help":
            print_help()
            continue

        if inp == "/version":
            from pyron.__init__ import __version__
            print(f"  pyron {__version__}")
            continue

        if inp == "/config":
            for k, v in get_api_config().items():
                print(f"  {_dim(k)}: {v}")
            continue

        if inp.startswith("/model "):
            m = inp[7:].strip()
            set_api_config(model=m)
            print(f"  model: {m}")
            cfg = get_api_config()
            continue

        if inp == "/clear":
            print("\033[2J\033[H", end="")
            print_help()
            continue

        if inp == "/chat":
            chat_only = not chat_only
            print(f"  chat {'on' if chat_only else 'off'}")
            continue

        if inp == "/memory":
            _show_memory_stats(agent.memory)
            continue

        if inp == "/forget":
            n = agent.memory.apply_forgetting(threshold=0.1)
            print(f"  pruned {n}")
            continue

        if inp.startswith("/plan "):
            goal = inp[6:].strip()
            if not goal:
                print("  specify a goal")
                continue
            agent = Agent(
                log_fn=lambda x: print(x, flush=True),
                status_fn=lambda x: print(x, end="", flush=True),
            )
            result = agent.run(goal)
            print(f"\n{result}\n")
            continue

        if chat_only:
            chat_history.append(Message("user", inp))
            try:
                r = agent.client.complete(chat_history)
                print(f"\n{r.content}\n")
                chat_history.append(Message("assistant", r.content))
            except Exception as e:
                print(f"\n  {_red(str(e))}\n")
        else:
            agent = Agent(
                log_fn=lambda x: print(x, flush=True),
                status_fn=lambda x: print(x, end="", flush=True),
            )
            try:
                result = agent.run(inp)
                print(f"\n{result}\n")
            except Exception as e:
                print(f"\n  {_red(str(e))}\n")


def main():
    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        print_help()
        return

    if "--model" in args:
        idx = args.index("--model")
        if idx + 1 < len(args):
            set_api_config(model=args[idx + 1])
            print(f"model: {args[idx + 1]}")
            return

    if args:
        goal = " ".join(args)
        agent = Agent(
            log_fn=lambda x: print(x, flush=True),
            status_fn=lambda x: print(x, end="", flush=True),
        )
        result = agent.run(goal)
        print(f"\n{result}\n")
        return

    interactive_loop()


if __name__ == "__main__":
    main()
