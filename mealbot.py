import argparse
from typing import Callable

from dotenv import load_dotenv

from agent import build_graph
from intake_agent import intake_complete

# Load ANTHROPIC_API_KEY from .env
load_dotenv()

EXIT_WORDS = {"end", "quit", "bye", "goodbye"}


def make_io(voice: bool) -> tuple[Callable[[], str], Callable[[str], None]]:
    """Return (get_input, send_output) functions for voice or text mode."""
    if voice:
        from voice import listen, speak

        def get_input() -> str:
            return listen()

        def send_output(text: str) -> None:
            print(f"Bot: {text}\n")
            speak(text)
    else:
        def get_input() -> str:
            return input("You: ").strip()

        def send_output(text: str) -> None:
            print(f"Bot: {text}\n")

    return get_input, send_output


def main() -> None:
    parser = argparse.ArgumentParser(description="Mealbot food ordering assistant")
    parser.add_argument("--voice", action="store_true", help="Enable voice input/output")
    args = parser.parse_args()

    get_input, send_output = make_io(args.voice)
    graph, config = build_graph()

    # Greet the user
    welcome = "Welcome to Mealbot! What would you like to order today?"
    send_output(welcome)
    if not args.voice:
        print("(Type 'bye' to exit)\n")

    # Conversation loop — each iteration is one user turn
    while True:
        try:
            user_input = get_input()
        except (KeyboardInterrupt, EOFError):
            send_output("Goodbye!")
            break

        if not user_input:
            continue

        if user_input.strip(".,!?").lower() in EXIT_WORDS:
            send_output("Goodbye! Have a great day!")
            break

        result = graph.invoke({"messages": [("user", user_input)]}, config)
        send_output(result["messages"][-1].content)

        if intake_complete(result):
            break


if __name__ == "__main__":
    main()
