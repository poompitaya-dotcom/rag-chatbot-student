"""Quality gate: run the golden dataset end to end and compare with the baseline.

pytest checks the deterministic parts (retrieval, the policy decision) and
must pass 100%. This gate checks the *generated answers*, which are fuzzier,
so it measures a pass rate per category and compares it with the last
accepted baseline. A change that lowers any category is rejected, even if
the overall score goes up.

    python -m src.gate                     # check the live prompt
    python -m src.gate --prompt v2         # try a candidate prompt
    python -m src.gate --update-baseline   # accept the current results

Exit code 0 = pass, 1 = regression, 2 = no baseline yet. CI uses the exit code.
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from src.golden import load_golden
from src.rag import PROMPT_VERSION, rag_answer

TESTS_DIR = Path(__file__).resolve().parent.parent / "tests"
BASELINE_PATH = TESTS_DIR / "gate_baseline.json"

# A generated "I do not know" counts as declining, just like a policy refusal.
DECLINE_MARKERS = ["i do not know", "i don't know", "don't have information"]


def passes(row, result):
    answer = result["answer"].lower()
    if row["expected_action"] == "refuse":
        return result["refused"] or any(m in answer for m in DECLINE_MARKERS)
    return not result["refused"] and all(f.lower() in answer for f in row["must_include"])


def run(prompt_version):
    golden = load_golden()
    scores = defaultdict(lambda: {"passed": 0, "total": 0})
    failures = []
    for row in golden:
        result = rag_answer(row["question"], prompt_version=prompt_version)
        ok = passes(row, result)
        scores[row["category"]]["total"] += 1
        scores[row["category"]]["passed"] += ok
        if not ok:
            failures.append((row["category"], row["question"], result["answer"]))
    return dict(scores), failures


def rate(score):
    return score["passed"] / score["total"] if score["total"] else 0.0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--prompt", default=PROMPT_VERSION, help="prompt version to evaluate")
    parser.add_argument("--update-baseline", action="store_true", help="save these results as the new baseline")
    args = parser.parse_args()

    print(f"Running the golden dataset with prompt {args.prompt} ...")
    scores, failures = run(args.prompt)

    baseline = None
    if BASELINE_PATH.exists():
        baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))

    regressions = []
    print(f"\n{'category':<20} {'now':>9} {'baseline':>9}")
    for category, score in sorted(scores.items()):
        now = f"{score['passed']}/{score['total']}"
        before = baseline["categories"].get(category) if baseline else None
        if before is None:
            print(f"{category:<20} {now:>9} {'new':>9}")
            continue
        flag = ""
        if rate(score) < rate(before):
            regressions.append(category)
            flag = "  <-- worse"
        then = f"{before['passed']}/{before['total']}"
        print(f"{category:<20} {now:>9} {then:>9}{flag}")

    overall = f"{sum(s['passed'] for s in scores.values())}/{sum(s['total'] for s in scores.values())}"
    print(f"{'overall':<20} {overall:>9}")

    if failures:
        print("\nFailing cases:")
        for category, question, answer in failures:
            print(f"  [{category}] {question}\n      -> {answer}")

    if args.update_baseline:
        BASELINE_PATH.write_text(
            json.dumps({"prompt_version": args.prompt, "categories": scores}, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"\nBaseline saved to {BASELINE_PATH.name}. Commit it: accepting a baseline is a reviewed decision.")
        return 0
    if baseline is None:
        print("\nNo baseline yet. Run `python -m src.gate --update-baseline` once with the live prompt.")
        return 2
    if regressions:
        print(f"\nGATE FAILED: {', '.join(regressions)} got worse than the baseline. Don't ship this change.")
        return 1
    print("\nGATE PASSED: no category got worse than the baseline.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
