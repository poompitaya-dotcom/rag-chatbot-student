# Prompt changelog

Every prompt is a file in this folder, and `PROMPT_VERSION` in `src/rag.py`
says which one is live. Never edit a released prompt in place: add a new
version, run the quality gate (`python -m src.gate --prompt <version>`),
and record the result here. Rolling back is then a one-line change.

| Version | Status | What changed | Gate result |
|---|---|---|---|
| v1 | **live** | The original prompt: answer briefly, only from the context, say "I do not know" otherwise. | Baseline |
| v2 | **rejected** | Friendlier persona; "answer by meaning"; "always give a helpful, complete answer". Aimed at the "I do not know" replies to paraphrased questions. | **FAILED** (2026-11-09): `out of scope` 6/6 → 3/6, `refund` 3/3 → 2/3. Overall 15/24 → 13/24. |

## v2 — rejected, 2026-11-09

`python -m src.gate --prompt v2` against the v1 baseline:

| category | v1 baseline | v2 | |
|---|---|---|---|
| account | 1/3 | 2/3 | better |
| delivery | 1/3 | 1/3 | — |
| out of scope | 6/6 | 3/6 | **worse** |
| refund | 3/3 | 2/3 | **worse** |
| returns | 3/6 | 4/6 | better |
| technical support | 1/3 | 1/3 | — |
| **overall** | **15/24** | **13/24** | |

**Why it was rejected.** v2 does what it set out to do — paraphrased `returns`
and `account` questions improved — but it pays for that with the two
categories we care about most:

- **`out of scope` 6/6 → 3/6.** v1's "If the information is unavailable, say
  'I do not know'" is the *only* thing enforcing AGENT_POLICY.md P6 for
  questions that score above the refusal threshold. v2 replaces it with
  "Always give a helpful, complete answer", so the model invents: it priced a
  product that does not exist (`How much is the LumaBox X999?` → `$99`),
  answered a moon-shipping question with the EMS returns policy, and gave an
  opinion on LumaBox as an investment. An invented price is the worst failure
  this bot has, because a customer cannot tell it apart from a real one.
- **`refund` 3/3 → 2/3.** "Answer briefly" is gone, so "How many days until my
  refund arrives?" came back as `8` instead of `8 business days` — the unit
  dropped, which is exactly the kind of answer that creates a support ticket.

It also started answering yes/no where the fact was wanted ("Is technical
support available on weekends?" → `No`, which is wrong), so the apparent
improvement elsewhere is not safely transferable.

**What a v3 would have to do.** Keep v1's two load-bearing instructions —
"answer briefly" and the explicit licence to say "I do not know" — and add
only the paraphrase tolerance. The gate is the acceptance test; a v3 ships
only if no category is below its baseline.

The overall score going *down* is not why it was rejected. The gate rejects a
per-category regression even when the overall number improves, because an
average hides exactly the trade-off v2 made.
