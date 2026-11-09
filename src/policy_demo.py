"""Compare the bot's answers with and without its policy check.

    python -m src.policy_demo              # the live prompt
    python -m src.policy_demo --prompt v2  # a candidate prompt
"""
import argparse

from src.rag import PROMPT_VERSION, rag_answer

QUESTIONS = [
    "What are your technical support hours?",
    "What's the weather like today?",
    "Who won the football match last night?",
    "Does LumaBox ship to the moon?",
    "How much is the LumaBox X999?",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--prompt", default=PROMPT_VERSION)
    args = parser.parse_args()

    print(f"Prompt {args.prompt}\n")
    for question in QUESTIONS:
        without = rag_answer(question, enforce_policy=False, prompt_version=args.prompt)
        try:
            with_policy = rag_answer(question, prompt_version=args.prompt)
            with_text = ("[refused] " if with_policy["refused"] else "") + with_policy["answer"]
        except NotImplementedError as e:
            with_text = f"(not built yet: {e})"
        print(question)
        print(f"  top similarity : {without['hits'][0]['similarity']:.2f}")
        print(f"  without policy : {without['answer']}")
        print(f"  with policy    : {with_text}\n")


if __name__ == "__main__":
    main()
