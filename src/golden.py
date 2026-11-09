"""Load the golden dataset from tests/golden.xlsx.

Edit the file in Excel, LibreOffice or Google Sheets. One row per test
question, on the sheet named "golden":

  id               groups the wordings of one case (the first row is usually
                   close to the policy text, the rest are how customers ask)
  category         topic; the gate reports a pass rate per category
  question         one wording - every row is a separate test
  must_include     short facts copied exactly from data/lumabox_policies.txt,
                   separated by ";" (leave empty for "refuse" rows)
  expected_action  "answer" or "refuse"
  known_issue      optional: why this question is a known, accepted failure

Used by tests/test_golden.py and src/gate.py.
"""
import datetime
from pathlib import Path

from openpyxl import load_workbook

GOLDEN_PATH = Path(__file__).resolve().parent.parent / "tests" / "golden.xlsx"
SHEET = "golden"
COLUMNS = ["id", "category", "question", "must_include", "expected_action", "known_issue"]


def _text(value, where):
    if value is None:
        return ""
    if isinstance(value, (datetime.date, datetime.time)):
        raise ValueError(
            f"{where}: Excel turned this cell into a date or time ({value}). "
            "Format the column as Text, or start the cell with an apostrophe, e.g. '24/7"
        )
    return str(value).strip()


def load_golden(path=GOLDEN_PATH):
    """Return one dict per question row, with must_include as a list."""
    sheet = load_workbook(path, read_only=True, data_only=True)[SHEET]
    rows = sheet.iter_rows(values_only=True)
    header = [_text(c, f"{path.name} header") for c in next(rows)]
    missing = [c for c in COLUMNS if c not in header]
    if missing:
        raise ValueError(f"{path.name}: missing column(s) {missing}")

    cases = []
    for n, values in enumerate(rows, start=2):
        cells = dict(zip(header, values))
        row = {c: _text(cells.get(c), f"{path.name} row {n}, column {c}") for c in COLUMNS}
        if not row["question"]:
            continue  # blank line
        if not row["id"] or not row["category"]:
            raise ValueError(f"{path.name} row {n}: id and category can't be empty")
        if row["expected_action"] not in ("answer", "refuse"):
            raise ValueError(
                f'{path.name} row {n}: expected_action must be "answer" or "refuse", '
                f'not {row["expected_action"]!r}'
            )
        row["must_include"] = [f.strip() for f in row["must_include"].split(";") if f.strip()]
        if row["expected_action"] == "answer" and not row["must_include"]:
            raise ValueError(f'{path.name} row {n}: an "answer" row needs at least one must_include fact')
        cases.append(row)
    return cases
