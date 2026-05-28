import sys
import shutil
import json
import time

from pyron.agent.agent import Agent
from pyron.api.client import ApiClient, Message
from pyron.config import get_api_config, set_api_config
from pyron.memory_manager import MemoryManager, SYSTEM_MASTER_PROMPT


def print_header():
    term_width = shutil.get_terminal_size().columns
    print("=" * term_width)
    print("  Pyron - Autonomous AI Agent with Hierarchical Memory".center(term_width))
    print(f"  Model: {get_api_config()['model']}  |  Effective Context: ~1M tokens".center(term_width))
    print("=" * term_width)
    print()


def print_help():
    print("Commands:")
    print("  /exit          - Exit Pyron")
    print("  /help          - Show this help message")
    print("  /config        - Show current configuration")
    print("  /model <m>     - Change model")
    print("  /clear         - Clear screen")
    print("  /chat          - Toggle free chat mode (agent with full tools)")
    print("  /memory        - Show memory layer statistics")
    print("  /forget        - Apply forgetting curve to prune old memories")
    print("  /plan <goal>   - Create and execute a plan for a goal")
    print()
    print("Usage: Just type anything. Pyron uses its memory to help you freely.")
    print()


def _show_memory_stats(memory: MemoryManager):
    stats = memory.get_stats()
    print(f"  Working Memory: {stats['working_items']} items ({stats['working_tokens']} tokens)")
    print(f"  Vector Store:   {stats['vector_items']} items")
    print(f"  Knowledge Graph: {stats['kg_entities']} entities, {stats['kg_relations']} relations")
    print(f"  Compressions:   {stats['compressions']}")
    print(f"  Interactions:   {stats['interactions']}")
    print(f"  Summaries:      ", end="")
    levels = []
    if stats["level1_summary"]:
        levels.append("Level 1")
    if stats["level2_summary"]:
        levels.append("Level 2")
    if stats["level3_summary"]:
        levels.append("Level 3")
    print(", ".join(levels) if levels else "None")
    print()


def interactive_loop():
    print_header()
    print_help()

    agent = Agent()
    chat_history = [Message("system", SYSTEM_MASTER_PROMPT)]
    free_mode = True

    while True:
        try:
            user_input = input("pyron> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting Pyron.")
            break

        if not user_input:
            continue

        if user_input == "/exit":
            print("Exiting Pyron.")
            break

        if user_input == "/help":
            print_help()
            continue

        if user_input == "/config":
            cfg = get_api_config()
            for k, v in cfg.items():
                print(f"  {k}: {v}")
            continue

        if user_input.startswith("/model "):
            model = user_input[7:].strip()
            set_api_config(model=model)
            print(f"Model set to: {model}")
            continue

        if user_input == "/clear":
            print("\033[2J\033[H", end="")
            print_header()
            continue

        if user_input == "/chat":
            free_mode = not free_mode
            print(f"{'Free chat mode with tools' if free_mode else 'Plan-execute mode'} {'ON' if free_mode else 'OFF'}")
            continue

        if user_input == "/memory":
            _show_memory_stats(agent.memory)
            continue

        if user_input == "/forget":
            pruned = agent.memory.apply_forgetting(threshold=0.1)
            print(f"Pruned {pruned} old memories.")
            continue

        if user_input.startswith("/plan "):
            goal = user_input[6:].strip()
            if not goal:
                print("Specify a goal: /plan <goal>")
                continue
            print(f"\n{'─' * shutil.get_terminal_size().columns}")
            print("  Planning and executing...")
            print(f"{'─' * shutil.get_terminal_size().columns}\n")
            result = agent.run(goal)
            print(f"\n{result}\n")
            continue

        agent.memory.save_interaction("user", user_input, importance=0.7, tags=["interactive"])
        chat_history.append(Message("user", user_input))

        try:
            response = agent.client.complete(chat_history)
            output = response.content
            print(f"\n{output}\n")
            agent.memory.save_interaction("assistant", output, importance=0.6, tags=["response"])
            chat_history.append(Message("assistant", output))
        except Exception as e:
            print(f"\n[Error] {e}\n")

        agent.memory.check_and_compress()
        agent.memory.apply_forgetting(threshold=0.05)


def main():
    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        print_help()
        return

    if "--model" in args:
        idx = args.index("--model")
        if idx + 1 < len(args):
            set_api_config(model=args[idx + 1])
            print(f"Model set to: {args[idx + 1]}")
            return

    if args:
        goal = " ".join(args)
        agent = Agent()
        result = agent.run(goal)
        print(result)
        return

    interactive_loop()


if __name__ == "__main__":
    main()
