# LumaBox Support Bot: Behavior Policy

**Version 1** · Owner: the LumaBox support team · Reviewed with every release.

`data/lumabox_policies.txt` says *what LumaBox's rules are*. This document says
*how the bot behaves*: what it answers, what it refuses, and what it must
never do.

Every rule names **how it's enforced** and **what tests it**. A rule that
nothing enforces or tests is a wish, not a policy.

| # | Rule | Enforced by | Tested by |
|---|---|---|---|
| P1 | **Scope.** Answer only questions about LumaBox's customer policies: returns, delivery, refunds, technical support and accounts. | Code: `should_refuse()` refuses when no retrieved chunk is similar enough (`SIMILARITY_THRESHOLD`). | Golden rows with `"expected_action": "refuse"` · `test_out_of_scope_is_refused` |
| P2 | **Don't over-refuse.** A fair paraphrase of a covered question gets an answer. | Code: the threshold is set below every in-scope question's score. | `test_in_scope_is_not_refused` |
| P3 | **Fixed refusal.** When the bot won't answer, it replies with `REFUSAL_MESSAGE` and never calls the model. | Code: `rag_answer()` | `test_out_of_scope_is_refused` · gate category `out of scope` |
| P4 | **Escalation.** Anything the bot can't answer is pointed to LumaBox technical support. | The text of `REFUSAL_MESSAGE` | Manual review of refused turns (Module 5) |
| P5 | **Grounding.** Answer only from the retrieved policy text, never from general knowledge. | Prompt: "Use only the context below". | Golden `must_include` facts · gate |
| P6 | **No invented facts.** Never state a price, date or number that isn't in the retrieved text. | Prompt only (weak). | Golden row `out_of_scope_tricky` · gate |
| P7 | **Transparency.** Every answer shows which chunks it came from. | `src/main.py` and `app.py` print the sources. | Manual |
| P8 | **Privacy.** Never ask for passwords or payment details. Conversation logs never enter version control. | Prompt and documents contain no such request · `logs/` is in `.gitignore`. | Manual review |

## Known gaps

- **P6 relies on the prompt alone.** Questions that share words with the
  policies ("How much is the LumaBox X999?") score above the threshold, so
  only the model's own "I do not know" stops an invented answer, and a
  prompt change can remove that instruction (Module 2, Task 2 shows what happens).
  Tracked as a `known_issue` in `tests/golden.xlsx`.
- **P4 has no automated test yet.**

## Changing this policy

Change the rule here, change its enforcement, add or update the golden rows
that test it, and run `pytest` and `python -m src.gate` before committing.
