"""Print the top retrieval similarity for some questions (Module 1, Task 3).

    python -m src.scores                          # the built-in examples
    python -m src.scores "my question" "another"  # your own questions

Similarity runs from about 0 (unrelated) to 1 (same meaning). Module 2, Task 3
uses these numbers to choose the refusal threshold.
"""
import sys

from src.rag import retrieve

EXAMPLES = [
    ("in scope", "What are your technical support hours?"),
    ("in scope", "When will I get my money back?"),
    ("in scope", "I can't sign in to my account."),
    ("in scope", "My package never arrived, who do I contact?"),
    ("out of scope", "What's the weather like today?"),
    ("out of scope", "Who won the football match last night?"),
    ("out of scope", "Can you recommend a good restaurant?"),
    ("out of scope?", "Does LumaBox ship to the moon?"),
]


def main():
    questions = [("", q) for q in sys.argv[1:]] or EXAMPLES
    print(f"{'top sim':>7}  {'chunk':<8} {'':<13} question")
    for label, question in questions:
        top = retrieve(question, k=1)[0]
        print(f"{top['similarity']:>7.2f}  {top['id']:<8} {label:<13} {question}")


if __name__ == "__main__":
    main()
