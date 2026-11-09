# Prompt changelog

Every prompt is a file in this folder, and `PROMPT_VERSION` in `src/rag.py`
says which one is live. Never edit a released prompt in place: add a new
version, run the quality gate (`python -m src.gate --prompt <version>`),
and record the result here. Rolling back is then a one-line change.

| Version | Status | What changed | Gate result |
|---|---|---|---|
| v1 | **live** | The original prompt: answer briefly, only from the context, say "I do not know" otherwise. | Baseline |
| v2 | **rejected** | Friendlier persona; "answer by meaning"; "always give a helpful, complete answer". Aimed at the "I do not know" replies to paraphrased questions. | **FAILED** (2026-11-09): `out of scope` 6/6 → 3/6, `refund` 3/3 → 2/3. Overall 15/24 → 13/24. |
| v3 | **rejected** | v1 plus "use the exact words of the context" and explicit permission to answer when the wording differs. Aimed at the generation errors found in the traffic replay. | **FAILED** (2026-11-09): `exchange` 1/3 → 0/3, `returns` 3/6 → 2/8, `technical support` 1/3 → 1/4. Overall 31/47 → 30/47. |
| v4 | **rejected** | v3 plus an explicit "never answer with only yes or no". | **FAILED** (2026-11-09), badly: 6 categories worse, overall 31/47 → 20/47. |

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

## v3 and v4 — rejected, 2026-11-09

Both were attempts to fix the **generation errors** the traffic replay turned
up (homework Exercise 2): questions where the right chunk *was* retrieved and
the model still answered "I do not know" — "Is support open on sundays?"
(the Technical Support chunk, retrieved first at 0.545, containing
"Available 24/7, every day"), "Can I return
something I bought online if I just don't like it?", "Can I swap my item for a
different model?".

**v3** keeps everything v1 says, including "answer briefly" and the licence to
say "I do not know", and adds only paraphrase tolerance. It was still rejected:

| category | baseline | v3 | |
|---|---|---|---|
| account | 1/3 | 2/3 | better |
| exchange | 1/3 | 0/3 | **worse** |
| returns | 3/6 | 2/8 | **worse** |
| technical support | 1/3 | 1/4 | **worse** |
| **overall** | **31/47** | **30/47** | |

It did not fix the target failure either: "Is support open on sundays?" went
from "I do not know" to "Yes." — fluent, confident, and missing the fact the
golden row asks for.

**v4** added one more instruction to v3: *never answer with only "yes" or
"no"*. The result is the clearest lesson of the whole exercise — naming the
tokens in the instruction made the model *produce* them. "What are your
technical support hours?" → `Yes.` "How do I reset my LumaBox account
password?" → `Yes.` "How much is the SonaBox Speaker?" → `yes`. Six categories
regressed and the overall score collapsed from 31/47 to 20/47, including
`price` 12/12 → 9/12 and `out of scope` 8/8 → 3/8.

**Conclusion.** v1 stays live. Three candidate prompts have now been measured
and all three were worse; the remaining generation errors look like a capacity
limit of flan-t5-base (250M parameters) on "Can I …?" and "Is … ?" phrasings,
not something a better instruction will fix. The next thing to try is a larger
generator, which is a model change and gets gated the same way. Both files are
kept rather than deleted, so the next person does not repeat the experiment.
