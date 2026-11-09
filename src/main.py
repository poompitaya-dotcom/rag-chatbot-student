"""Command-line chat loop for the local RAG chatbot.

Run:
    python -m src.main
Type 'exit' or press Ctrl+C to quit.

Replay a file of questions, one per line (homework Exercise 2):
    python -m src.main --replay homework/traffic.txt

Every turn is traced to logs/turns.jsonl (Module 5).
You shouldn't need to change this file.
"""
import argparse

from src.monitoring import log_turn
from src.rag import rag_answer


def answer(question, channel):
    result = rag_answer(question)
    log_turn(result, channel=channel)
    print(f"Bot: {result['answer']}")
    print(f"  (sources: {[h['id'] for h in result['hits']]})")


def main():
    parser = argparse.ArgumentParser(description="LumaBox support bot")
    parser.add_argument("--replay", metavar="FILE", help="answer every line of FILE instead of chatting")
    args = parser.parse_args()

    if args.replay:
        with open(args.replay, encoding="utf-8") as f:
            questions = [line.strip() for line in f if line.strip()]
        for question in questions:
            print(f"\nYou: {question}")
            answer(question, channel="replay")
        return

    print("LumaBox support bot (type 'exit' to quit)")
    while True:
        try:
            question = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break
        if question.lower() in {"exit", "quit"}:
            print("Bye!")
            break
        if not question:
            continue
        answer(question, channel="cli")


if __name__ == "__main__":
    main()
