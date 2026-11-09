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
| P9 | **Prices come from the table, never from the model.** The bot may state a price only when that price is in `homework/model_prices.xlsx` and the matching sentence was retrieved into the context. | Knowledge: `price_documents()` in `src/ingest.py` indexes one sentence per row into the same collection as the policies, so a price can only reach the answer by being retrieved · Prompt: "Use only the context below" (P5) | Golden `price` rows with the exact figure in `must_include` · gate category `price` |
| P10 | **Unknown products get no price.** For a product that is not in the price table, the bot must not answer with a price. | Prompt only (weak), as for P6: a question about an unlisted model still retrieves a *real* price sentence, so `should_refuse()` cannot catch it. | Golden row `out_of_scope_tricky` ("How much is the LumaBox X999?") · gate category `out of scope` |
| P11 | **Prices are indicative, not a quote.** The bot never states stock, discounts, promotions, instalments or a total including shipping or tax — only the listed price of a listed product. | No such data is in the index, so nothing can be retrieved to support it · P5 then applies | Golden `refuse` rows for instalments and discounts |

## Known gaps

- **P6 relies on the prompt alone.** Questions that share words with the
  policies ("How much is the LumaBox X999?") score above the threshold, so
  only the model's own "I do not know" stops an invented answer, and a
  prompt change can remove that instruction (Module 2, Task 2 shows what happens).
  Tracked as a `known_issue` in `tests/golden.xlsx`.
- **P4 has no automated test yet.**
- **P10 is the price-shaped version of P6, and it is weaker.** Before the
  price table was indexed, "How much is the LumaBox X999?" retrieved the
  Returns policy and the model had nothing numeric to copy. Now it retrieves
  a *real* price sentence for a *different* product at a similarity of 0.72,
  so the refusal threshold is useless here and only the model's own "I do not
  know" stands between the customer and a wrong price. It currently declines,
  which is the right answer for the wrong reason: nothing enforces it. A real
  fix is to check the model name in the question against the table before
  answering, and refuse when there is no exact match.
- **Serial codes are not understood.** "How much does model LMX-201 cost?"
  retrieves `price_1` (LMX-202, the X200), not `price_0`. To an embedding
  model, two serial codes that differ by one digit are nearly identical, and
  the codes carry no meaning to begin with. The bot currently declines rather
  than quoting the sibling's price, but that is luck, not enforcement; the
  fix is lexical (exact/keyword) matching alongside the vector search.

## Changing this policy

Change the rule here, change its enforcement, add or update the golden rows
that test it, and run `pytest` and `python -m src.gate` before committing.
