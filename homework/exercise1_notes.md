# Exercise 1 — A second knowledge source: prices

## What I built

`homework/model_prices.xlsx` (8 rows: `model`, `price`) is now a second
knowledge source in **the same Chroma collection** as the policy chunks.

- **`src/ingest.py`** gained `price_documents()`, which reads the sheet with
  `pandas.read_excel` and turns each row into one sentence:
  `The LMX-202 LumaBox X200 costs 4990 THB.` A table cell is not a
  retrievable unit — `4990` on its own means nothing to an embedding model —
  so the sentence has to carry the product name and the figure together. The
  messy `model` column (serial code and name run together) is kept verbatim,
  so a customer who quotes either the name or the code has something to match.
- The sentences are added to the same collection with ids `price_0 … price_7`
  and `metadatas={"source": "price"}`. **One collection, one retrieval path.**
  A separate price collection with my own "is this a price question?" router
  would be a second place for the bot to be wrong, would need its own tests,
  and is explicitly not accepted. The `source` metadata is for provenance, not
  routing — nothing in `retrieve()` branches on it.
- `KB_VERSION` now hashes the policy file **and** the price table, so changing
  a price changes the version stamped on every trace. A price change is a
  knowledge change; if it were invisible in the traces, a wrong price could
  never be traced back to the table that produced it.

`python -m src.ingest` now prints:

```
Indexed 5 policy chunks and 8 price rows into .../chroma_db (kb_version 7fba8726128a)
```

## Policy changes (`AGENT_POLICY.md`)

Three new rules, each with how it is enforced and what tests it:

| # | Rule | Enforced by | Tested by |
|---|---|---|---|
| P9 | A price may be stated only if it is in the table and its sentence was retrieved | Knowledge: prices only exist in the index; prompt P5 "use only the context" | `price` golden rows with the exact figure in `must_include`; gate category `price` |
| P10 | No price for a product that is not in the table | Prompt only — **weak**, see below | `out_of_scope_tricky` row; gate category `out of scope` |
| P11 | Prices are indicative: no stock, discounts, promotions or instalments | Nothing in the index supports those claims, then P5 | New `price_terms` refuse rows |

Two entries were added to **Known gaps**. P10 is the price-shaped version of
P6 and it is *weaker than P6 used to be*: before the table existed, "How much
is the LumaBox X999?" retrieved the Returns policy and the model had no number
to copy. Now it retrieves a **real price sentence for a different product** at
similarity 0.72, so `should_refuse()` is useless here and only the model's own
"I do not know" prevents a wrong price reaching a customer. The second gap is
serial codes: "How much does model LMX-201 cost?" retrieves `price_1`
(LMX-202, the X200), not `price_0` — one digit apart means nearly identical to
an embedding model, and the codes carry no meaning at all.

## Golden dataset

14 rows added (24 → 38 questions):

- `price_x200`, `price_sonabox_speaker`, `price_pro_x300`,
  `price_sonacube_earphone` — four cases, three wordings each,
  `must_include` the exact figure (`4990`, `1990`, `9990`, `1290`).
  Two of the four are **not LumaBox products**, which is the case that
  proves the bot answers from the table and not from the brand name.
- `price_terms` — two `refuse` rows (instalments, discounts) carrying a
  `known_issue`, because they retrieve a real price sentence above the
  threshold and so cannot be refused by `should_refuse()`. They are kept and
  documented rather than reworded until they pass.

## Gate: before and after

**Before** (v1 baseline, policies only, 24 questions):

```
category                   now  baseline
account                    1/3       new
delivery                   1/3       new
out of scope               6/6       new
refund                     3/3       new
returns                    3/6       new
technical support          1/3       new
overall                  15/24
```

**After** (v1, policies + prices, 38 questions):

```
category                   now  baseline
account                    1/3       1/3
delivery                   1/3       1/3
out of scope               8/8       6/6
price                    12/12       new
refund                     3/3       3/3
returns                    3/6       3/6
technical support          1/3       1/3
overall                  29/38

GATE PASSED: no category got worse than the baseline.
```

`pytest`: **65 passed, 5 xfailed** (the three `out_of_scope_tricky` rows plus
the two new `price_terms` rows).

**No existing category lost a single point.** That was the thing most at risk:
with 8 more chunks competing at `k = 2`, a policy question could easily have
had a price sentence crowd out its evidence. It did not — `out of scope` even
went 6/6 → 8/8 on a larger set. On that basis the baseline was updated
(`python -m src.gate --update-baseline`), which is a reviewed decision and is
recorded in the commit message.

## What the bot says for "How much is the LumaBox X999?"

```
You: How much is the LumaBox X999?
Bot: I do not know
  (sources: ['price_1', 'price_0'])
```

It declines — but **for the wrong reason, and nothing enforces it.** The
sources tell the real story: it retrieved the X200 and X100 price sentences at
0.72 similarity, well above the 0.30 refusal threshold, so the policy check
passed the question straight through to the model. flan-t5 then chose not to
copy a number it could not match to the product. That is the model's judgement
on this particular wording, not a guarantee — and with prompt v2 in Module 3
the same question produced an invented `$99`.

So the row stays in the golden dataset as an `out_of_scope_tricky` row with
its `known_issue`, exactly as before. The honest status is: *currently passes,
not currently enforced.* A real fix is a check of the model name in the
question against the table before the generator is called, refusing when there
is no exact match — the same lexical matching the serial-code gap needs.

Verified alongside it, the real products answer correctly and the policy
answers are unchanged:

| Question | Answer | Sources |
|---|---|---|
| How much is the LumaBox X200? | `4990 THB` | price_1, price_0 |
| What's the price of the SonaBox Speaker? | `1990 THB` | price_5, price_6 |
| How much is the LumaBox Pro X300? | `9990 THB` | price_4, price_0 |
| How much does the PotaBox Portable Screen cost? | `6990 THB` | price_7, price_4 |
| How much does model LMX-201 cost? | `I do not know` | price_1, price_2 (**wrong rows** — serial-code gap) |
| How much is the LumaBox X999? | `I do not know` | price_1, price_0 |
| What are your technical support hours? | `24/7, every day.` | chunk_3, chunk_0 |
| How long does a refund take to process? | `8 business days` | chunk_2, chunk_0 |
