"""Review the logged traces: what a support team looks at every week.

    python -m src.review                 # summary, flagged turns, random sample
    python -m src.review --sample 10     # bigger random sample
    python -m src.review --no-sentiment  # skip the sentiment pass (faster)

Nobody reads every conversation. You read (1) everything a rule flags and
(2) a random sample of the rest, because the flags only catch the failures
you already thought of.
"""
import argparse
import random
import statistics

from src.monitoring import LOG_PATH, read_turns
from src.rag import SIMILARITY_THRESHOLD, generate_answer

# Answered, but only just above the refusal threshold: worth a look.
LOW_CONFIDENCE_MARGIN = 0.10
DECLINE_MARKERS = ["i do not know", "i don't know"]

# Sentiment analysis with the model we already have: flan-t5 was trained on
# questions in exactly this options format. It over-flags a little (e.g.
# "I forgot my password" reads as negative), which is fine for triage:
# a flag means "a human should read this", not "this user is angry".
SENTIMENT_PROMPT = "Message: {message}\nIs this message negative?\nOPTIONS:\n- yes\n- no"


def is_negative(message):
    return generate_answer(SENTIMENT_PROMPT.format(message=message)).strip().lower() == "yes"


def flags_for(turn, with_sentiment):
    flags = []
    if turn["refused"]:
        flags.append("refused")
    elif any(m in turn["answer"].lower() for m in DECLINE_MARKERS):
        flags.append("model declined")
    elif turn["top_similarity"] is not None and turn["top_similarity"] < SIMILARITY_THRESHOLD + LOW_CONFIDENCE_MARGIN:
        flags.append("low confidence")
    if with_sentiment and is_negative(turn["question"]):
        flags.append("negative sentiment")
    return flags


def show(turn, flags=()):
    tag = f"  [{', '.join(flags)}]" if flags else ""
    print(f"- {turn['trace_id']}{tag}")
    print(f"    Q: {turn['question']}")
    print(f"    A: {turn['answer']}")
    print(f"    top similarity {turn['top_similarity']}, retrieved {[r['id'] for r in turn['retrieved']]}, "
          f"prompt {turn['prompt_version']}, kb {turn['kb_version']}")


def percentile(values, p):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(p / 100 * (len(ordered) - 1))))]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sample", type=int, default=5, help="how many unflagged turns to sample")
    parser.add_argument("--seed", type=int, default=0, help="random seed, so a review can be repeated")
    parser.add_argument("--no-sentiment", action="store_true")
    args = parser.parse_args()

    turns = read_turns()
    if not turns:
        print(f"No traces in {LOG_PATH} yet. Chat with `python -m src.main` first.")
        return

    latencies = [t["timings_ms"]["retrieve"] + t["timings_ms"]["generate"] for t in turns]
    refused = sum(t["refused"] for t in turns)
    print(f"{len(turns)} turns, {turns[0]['time']} to {turns[-1]['time']}")
    print(f"refusal rate {refused / len(turns):.0%} · latency median {statistics.median(latencies):.0f} ms, "
          f"p95 {percentile(latencies, 95):.0f} ms")
    print(f"prompt versions {sorted({t['prompt_version'] for t in turns})} · "
          f"kb versions {sorted({t['kb_version'] for t in turns})}")

    flagged, unflagged = [], []
    for turn in turns:
        flags = flags_for(turn, not args.no_sentiment)
        (flagged if flags else unflagged).append((turn, flags))

    print(f"\nFLAGGED ({len(flagged)}): read every one")
    for turn, flags in flagged:
        show(turn, flags)

    sample = random.Random(args.seed).sample(unflagged, min(args.sample, len(unflagged)))
    print(f"\nRANDOM SAMPLE ({len(sample)} of {len(unflagged)} unflagged): the failures no rule catches")
    for turn, _ in sample:
        show(turn)


if __name__ == "__main__":
    main()
