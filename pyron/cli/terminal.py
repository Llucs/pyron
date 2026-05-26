import sys
import shutil

from pyron.agent.agent import Agent
from pyron.api.client import ApiClient, Message
from pyron.config import get_api_config, set_api_config


def print_header():
    term_width = shutil.get_terminal_size().columns
    print("=" * term_width)
    print("  Pyron - Autonomous AI Agent".center(term_width))
    print(f"  Model: {get_api_config()['model']}".center(term_width))
    print("=" * term_width)
    print()


def print_help():
    print("Commands:")
    print("  /exit       - Exit Pyron")
    print("  /help       - Show this help message")
    print("  /config     - Show current configuration")
    print("  /model <m>  - Change model")
    print("  /clear      - Clear screen")
    print("  /chat       - Enter chat mode (no tool execution)")
    print()
    print("Usage: Enter a goal for Pyron to execute autonomously.")
    print()


def chat_mode():
    print("Entering chat mode. Type /back to return.")
    client = ApiClient()
    history = [Message("system", "You are Pyron, an autonomous AI assistant.")]

    while True:
        try:
            user_input = input("chat> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue
        if user_input == "/back":
            break

        history.append(Message("user", user_input))
        response = client.complete(history)
        print(f"\n{response.content}\n")
        history.append(Message("assistant", response.content))


def interactive_loop():
    print_header()
    print_help()

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
            chat_mode()
            continue

        agent = Agent()
        print(f"\n{'─' * shutil.get_terminal_size().columns}")
        print("  Processing goal...")
        print(f"{'─' * shutil.get_terminal_size().columns}\n")

        result = agent.run(user_input)
        print(f"\n{result}\n")


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

    if args and args[0] == "chat":
        chat_mode()
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
