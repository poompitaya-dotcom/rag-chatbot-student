# Reflection — Where would you fix it?

Four things go wrong with the LumaBox bot after launch. For each: where the fix
belongs, what I would change, and how I would know it worked.

---

## 1. A customer has asked about their refund three times. Each time the bot says "I do not know" or refuses, and the customer is getting angry.

**Where:** two places, and it matters which comes first. Immediately, this is
**outside the bot** — a customer on their third attempt needs a human, not a
better answer. In the system, it is a **retrieval/threshold** problem, not a
knowledge one: the refund policy *is* in `data/lumabox_policies.txt`, so the
bot is failing on this customer's *wording*, not on the fact.

**What I would change:** first, a policy rule (and the `REFUSAL_MESSAGE` path)
that escalates to a human after two consecutive refusals or declines in one
conversation — the bot's job is to end the loop, not to repeat itself.
Then I would take the customer's actual wordings out of `logs/turns.jsonl`,
add them to `tests/golden.xlsx` under `refund_time`, and look at the trace: a
low `top_similarity` on a fair question is a retrieval miss (fix by chunking,
lexical matching, or lowering `SIMILARITY_THRESHOLD`), while a good similarity
with "I do not know" is a generation error (fix as a new prompt version through
the gate).

**How I would know:** those new golden rows go from failing to passing, the
`refund` gate category does not drop, and in the next week's review the
refusal rate for refund questions falls and no conversation shows three
refusals in a row.

---

## 2. LumaBox changes its refund time from 8 to 5 business days.

**Where:** the **knowledge**, and only the knowledge. Nothing about the code,
the prompt or the policy is wrong — the document is simply out of date. The
content owner (the support team) edits
`data/lumabox_policies.txt`; this is exactly the property RAG buys us, since
changing what the bot knows needs no retraining.

**What I would change:** the sentence in the policy file, then
`python -m src.ingest` to rebuild the index, then every golden row whose
`must_include` says `8 business days` — those tests are *supposed* to break, and
a change of fact that breaks no test would mean the fact was never tested.
`KB_VERSION` changes automatically with the file's hash, so traces from before
and after the change are distinguishable.

**How I would know:** `pytest` fails on the old `8 business days` rows before I
update them and passes after; the gate's `refund` category holds at its
baseline; the bot answers "5 business days"; and `python -m src.review` shows
the new `kb_version` on live turns, which is the proof that the deployed
containers actually picked up the new index.

---

## 3. A teammate writes a new prompt that makes the answers friendlier and wants it live today.

**Where:** the **tests and gate**. The question "is this better?" is not
answered by reading the prompt or trying three questions by hand; it is
answered by the golden dataset. The process already exists and does not need
bending for an urgent request.

**What I would change:** nothing yet. The prompt goes in as a new file
(`prompts/answer_v3.txt`) — never an edit to a released one — and gets
`python -m src.gate --prompt v3`. If no category is worse, I flip
`PROMPT_VERSION`, record the gate result in `prompts/CHANGELOG.md`, and let the
pipeline ship it; that genuinely can be the same day. If a category is worse, it
is rejected and the changelog says why. This is precisely what happened to v2 in
Module 3: friendlier wording cost us `out of scope` (6/6 → 3/6) and `refund`
(3/3 → 2/3), because "always give a helpful, complete answer" also removes the
model's licence to say "I do not know" — and that licence was the only thing
enforcing P6.

Three candidate prompts have now been through this process and all three were
rejected — v2, and then v3 and v4 in the homework. v4 is the one to remember:
adding "never answer with only yes or no" made flan-t5 answer "Yes." to
everything, and the overall score fell from 31/47 to 20/47. No amount of
reading the prompt would have predicted that.

**How I would know:** the gate's per-category table *is* the answer, and it is
checked again in CI on push, so the decision cannot be bypassed by someone
editing the live prompt. Rolling back is a one-line change of
`PROMPT_VERSION`, which is why versioned prompt files are worth the trouble.

---

## 4. The day after a release, the refusal rate jumps from 20% to 60%.

**Where:** **monitoring** finds it, but the fix is wherever the release
touched. The jump is the alarm, not the diagnosis.

**What I would change:** first diagnose from the traces. `python -m src.review`
prints the refusal rate alongside `prompt_version` and `kb_version`, so I would
compare the turns before and after the release. A refusal is produced by
`should_refuse()` alone, so a jump means either `SIMILARITY_THRESHOLD` moved,
or the *scores* moved — a re-ingest that changed the chunking or dropped
content, a changed embedding model, or in the worst case an index built from a
truncated document. If `top_similarity` on ordinary in-scope questions has
fallen, it is the knowledge or the chunking; if the scores look normal and only
the decision changed, it is the threshold. Meanwhile I would roll back to the
previous image by its commit tag rather than debug in production.

**How I would know:** the refusal rate returns to its previous level on live
traffic; and before closing it out, the questions that were wrongly refused go
into `tests/golden.xlsx` so this particular regression can never ship again.
The honest conclusion from this one is that the gate did not catch it, so it
also belongs in CI: a check that the overall refusal rate on the golden dataset
has not moved more than a few points from the baseline.

---

## What the four have in common

The model is the same in all four cases. Each fix lands somewhere else — the
documents, the prompt, the policy, the threshold, the tests, the pipeline, or a
human — and the system is only debuggable because every answer is traced back
to the `prompt_version` and `kb_version` that produced it. Each fix also ends
the same way: the failure becomes a permanent row in the golden dataset, so the
test suite grows with every incident instead of staying at whatever we
imagined before launch.
