# Monitoring report

## Module 5, Task 3 — three classified failures

Traffic generated with `python -m src.main` and reviewed with
`python -m src.review --sample 5`.

Run summary: 8 turns, refusal rate 38%, latency median 228 ms / p95 250 ms,
prompt `v1`, kb `a959f3cca0fb`. 7 of 8 turns flagged.

| trace id | question | answer | top sim | retrieved | failure type | fixed in |
|---|---|---|---|---|---|---|
| `9eeb8a118466` | I forgot my pasword | *(refusal)* | 0.189 | chunk_4, chunk_1 | **Wrongly refused** | the policy threshold / retrieval |
| `76c572ac1ad5` | Do you offer exchanges instead of refunds? | I do not know. | 0.416 | chunk_0, chunk_2 | **Knowledge gap** | the documents |
| `7cc9541571d4` | Can I return a faulty item by messenger? | I do not know | 0.541 | chunk_0, chunk_1 | **Generation error** | a new prompt version, or the model |

### `9eeb8a118466` — "I forgot my pasword" → wrongly refused

The account policy *does* answer this. One transposed letter ("pasword")
pushed the top similarity to 0.189, under `SIMILARITY_THRESHOLD = 0.30`, so
`should_refuse()` refused before the generator was ever called. Note that
chunk_4 — the account policy, the correct chunk — was still ranked first: the
retrieval ordering was right and only the *confidence* was wrong, which is
what makes this a policy-decision failure rather than a retrieval miss.

**Where I would fix it:** the policy/retrieval boundary. Three options, in
increasing order of cost: lower the threshold (cheap, but 0.189 is close
enough to the unrelated-question range that it would start letting real
out-of-scope questions through); add lexical/keyword matching next to the
vector search, which handles the typo on the token "password"; or run a
spelling correction over the query. The threshold alone cannot fix this
safely, which is the honest answer. Either way, the question goes into
`tests/golden.xlsx` first so it fails before it passes.

### `76c572ac1ad5` — "Do you offer exchanges instead of refunds?" → knowledge gap

The bot is right to decline. It retrieved the closest things it has (Returns
at 0.416, Refund) and neither mentions exchanges, because **no LumaBox policy
covers exchanges at all**. Nothing in the retrieval, the prompt or the policy
is broken.

**Where I would fix it:** the documents, and not by me. The content owner —
LumaBox's support team — decides whether exchanges exist and writes the rule;
then `python -m src.ingest` re-indexes and `KB_VERSION` changes. This is the
most valuable thing monitoring finds, because it is a gap in the *business's*
written policy that only showed up once customers started asking.

### `7cc9541571d4` — "Can I return a faulty item by messenger?" → generation error

The most interesting one. Retrieval worked perfectly: chunk_0 at 0.541 is the
Returns policy, and it contains the literal sentence "a messenger will pick up
the item within 10 km of the store". The evidence was in the prompt and the
model still answered "I do not know". A row with `must_include: messenger`
would *pass* `pytest` (the retrieval test) and *fail* the gate (the generated
answer) — which is exactly the split the two tools are meant to expose.

**Where I would fix it:** a new prompt version, put through
`python -m src.gate` like any other release. flan-t5-base is small and
over-declines on yes/no questions phrased as "Can I ...?"; the v2 experiment in
Module 3 showed that pushing the model to always answer costs us the
`out of scope` category, so a v3 has to buy paraphrase tolerance without
removing the "I do not know" licence. Failing that, the fix is a bigger
generator, not a better prompt.

### Note on the flag rate

7 of 8 turns were flagged, which looks alarming and is not. `src/review.py`
flags "refused", "model declined", "low confidence" and "negative sentiment",
and the sentiment pass over-flags by design ("I forgot my pasword" and "Can I
return a faulty item by messenger?" both read as negative to flan-t5). A flag
means *a human should read this*, not *this is a failure* — and `Thanks, that
was helpful` being refused is the clearest example: the refusal is correct
behaviour for a message that is not a question at all, not a bug.
