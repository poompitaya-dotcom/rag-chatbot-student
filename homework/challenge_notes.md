# Challenge — Exact model names and serial codes (hybrid search)

Part 1 of the optional challenge. Part 2 (pushing to GitHub and getting the
`test` job green in the Actions tab) is **not done**: it needs a GitHub
account and a push, which is outside what this submission covers. The project
is ready for it — `.github/workflows/ci.yml` runs `python -m src.ingest`,
`pytest` and `python -m src.gate`, and `tests/gate_baseline.json` is
committed, which is the thing CI has no way to recreate on its own.

## Why vector search alone gets model codes wrong

An embedding model maps text to a point in space by **meaning**, and these
tokens have almost none. `X200` and `X250` sit in nearly the same place
because they are the same shape of string in the same kind of sentence; the
digits that distinguish them are the least semantically loaded characters in
the product name. Serial codes are worse: `LMX-201` and `LMX-202` are, to the
model, one unfamiliar token each, differing in a character that carries no
meaning. This is also the one case where the customer is being *maximally
precise* — somebody who types a serial code has read it off the box — so the
system is least reliable exactly where the user is most specific. Chunking,
more context or a bigger generator do not help; the information the ranker
needs is literal, and vectors throw literal away.

Measured before the fix:

| question | retrieved | should have been |
|---|---|---|
| How much does model LMX-201 cost? | `price_1` (LMX-202, X200) at 0.712 | `price_0` (LMX-201, X100) |
| How much does model SNB-SPK1 cost? | wrong sibling row | `price_5` |

The bot answered "I do not know" to both, which is luck: the retrieved context
contained a real, wrong price, and a model willing to copy it — prompt v2, for
instance — would have quoted the X200's price for an X100.

## The fix

`retrieve()` in `src/rag.py` now re-ranks a candidate pool rather than
returning Chroma's order directly:

1. ask Chroma for `CANDIDATE_POOL = 10` nearest chunks;
2. score each one lexically against the query;
3. rank on `max(vector_similarity, 0.8 × lexical_score)`;
4. break ties on `lexical_precision`.

`lexical_score` takes the better of two components:

- **code match** — the share of digit-bearing query tokens (`lmx-201`,
  `x300`, `48213`) found *exactly* in the document. All-or-nothing on purpose:
  a customer who types a code means that product and no other.
- **word overlap** — the share of the query's content words found in the
  document, with approximate matching for tokens of 6+ characters so a typo
  is forgiven. Short tokens must match exactly, or near-misses like
  "pay"/"pays" start accumulating a score on unrelated questions.

`max()` rather than a weighted sum: either signal on its own is sufficient
evidence, and averaging would let a perfect code match be diluted by a
mediocre vector score.

**The tie-break** was needed for one case the code match alone cannot settle.
"How much is the LumaBox X300?" matches `x300` exactly in *both*
`LMX-204 LumaBox X300` and `LMX-205 LumaBox Pro X300`, so both score 1.0 and
the vector model broke the tie the wrong way — the bot quoted 9990 (the Pro)
for a question about the X300. `lexical_precision` measures how much of the
*document* the query accounts for: the non-Pro row has no unexplained "Pro" in
it, so it wins. It is used only for ordering and never changes the similarity
a trace reports.

## Results

12 golden rows added (59 questions in total): one for every serial code in
`homework/model_prices.xlsx`, plus the product names not yet covered
(X100, X250, X300, PotaBox Portable Screen).

**None of them needed a `known_issue`.** The challenge expects these rows to
be added as known failures first and un-marked once hybrid search lands; here
the retrieval fix was already in place from Exercise 2, so they passed on the
first run — except the X300 ambiguity above, which produced a real gate
failure (`price` 23/24 `<-- worse`) and drove the tie-break.

> `pytest` **107 passed, 5 xfailed** · gate **45/59, GATE PASSED**
> `price` 12/12 → **24/24**; every other category unchanged.

Worth noting what is *not* fixed: `How much is the LumaBox X999?` still
retrieves a real price sentence at 0.72 and is still stopped only by the
model's own refusal to answer. Hybrid search makes the bot better at finding
the right product; it does nothing about a product that does not exist. That
remains the P10 gap in `AGENT_POLICY.md`, and the fix for it is a different
one — check the model name in the question against the table and refuse when
there is no exact match.

## What a real implementation would change

`lexical_score` is a plain token-overlap measure, not BM25: it has no term
frequency, no document-length normalisation and no inverse document frequency,
so a word that appears in every chunk ("LumaBox") counts as much as one that
appears in a single chunk. With 15 documents that is invisible; with 15,000 it
would start ranking badly, and `rank_bm25` or Chroma's own full-text index
would be the right call. The candidate-pool design is the part that carries
over: re-ranking the top N of a vector search, rather than scoring the whole
collection, is how this stays affordable as the index grows.
