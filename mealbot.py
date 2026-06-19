import argparse

from dotenv import load_dotenv

from agent import build_agent

load_dotenv()


def main() -> None:
    parser = argparse.ArgumentParser(description="Mealbot food ordering assistant")
    parser.add_argument("--voice", action="store_true", help="Enable voice input/output")
    args = parser.parse_args()

    if args.voice:
        from voice import listen, speak

    graph, config = build_agent()

    welcome = "Welcome to Mealbot! What would you like to order today?"
    print(welcome)
    if args.voice:
        speak(welcome)
    else:
        print("(Type 'bye' to exit)\n")

    while True:
        try:
            if args.voice:
                user_input = listen()
            else:
                user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            goodbye = "Goodbye!"
            print(f"\n{goodbye}")
            if args.voice:
                speak(goodbye)
            break

        if not user_input:
            continue

        if user_input.strip(".,!?").lower() in {"end", "quit", "bye", "goodbye"}:
            goodbye = "Goodbye! Have a great day!"
            print(f"Bot: {goodbye}\n")
            if args.voice:
                speak(goodbye)
            break

        result = graph.invoke({"messages": [("user", user_input)]}, config)
        reply = result["messages"][-1].content
        print(f"Bot: {reply}\n")
        if args.voice:
            speak(reply)

        order_placed = any(
            getattr(m, "name", None) == "send_order"
            for m in result["messages"]
        )
        if order_placed:
            break


if __name__ == "__main__":
    main()
