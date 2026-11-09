"""Golden dataset tests: run every question in tests/golden.xlsx.

A golden dataset is a curated, version-controlled list of questions with the
outcome each one must produce. You run the whole list after every change -
to the documents, the chunking, the model, the prompt, the policy - and it
tells you whether the change helped or broke something.

Each row is one question. Rows that share an id are wordings of the same
case: real users never type the policy's wording, so every wording is a
test case.

These tests check the deterministic parts and must all pass:
  - "answer" rows: the retrieved chunks contain every "must_include" fact;
  - "refuse" rows: the policy check refuses them;
  - "answer" rows: the policy check does NOT refuse them.
The generated answers are checked by the quality gate instead
(python -m src.gate), because model wording is fuzzier.

TODO T2: add rows to tests/golden.xlsx - see the guide, Module 3, Task 1.

Run from the project folder with:
    pytest
"""
import pytest

from src.golden import load_golden
from src.rag import retrieve, should_refuse

GOLDEN = load_golden()


def cases(action):
    """One pytest case per question row with this action."""
    params = []
    for row in GOLDEN:
        if row["expected_action"] != action:
            continue
        # A row with "known_issue" is a failure you've investigated and kept on
        # purpose. It's reported as "xfail" instead of breaking the suite, and
        # strict=True makes pytest tell you when it unexpectedly starts passing.
        marks = []
        if row.get("known_issue"):
            marks = [pytest.mark.xfail(reason=row["known_issue"], strict=True)]
        params.append(pytest.param(row, row["question"], id=f'{row["id"]}: {row["question"]}', marks=marks))
    return params


@pytest.mark.parametrize("row, question", cases("answer"))
def test_retrieval_finds_the_evidence(row, question):
    hits = retrieve(question, k=2)
    retrieved_text = "\n".join(h["text"] for h in hits)
    missing = [fact for fact in row["must_include"] if fact not in retrieved_text]
    assert not missing, f"retrieved {[h['id'] for h in hits]}, but they don't contain {missing}"


@pytest.mark.parametrize("row, question", cases("refuse"))
def test_out_of_scope_is_refused(row, question):
    hits = retrieve(question, k=2)
    assert should_refuse(hits), f"not refused: top similarity {hits[0]['similarity']:.3f}"


@pytest.mark.parametrize("row, question", cases("answer"))
def test_in_scope_is_not_refused(row, question):
    hits = retrieve(question, k=2)
    assert not should_refuse(hits), f"wrongly refused: top similarity {hits[0]['similarity']:.3f}"
