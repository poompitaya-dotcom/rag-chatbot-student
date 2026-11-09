# Prompt changelog

Every prompt is a file in this folder, and `PROMPT_VERSION` in `src/rag.py`
says which one is live. Never edit a released prompt in place: add a new
version, run the quality gate (`python -m src.gate --prompt <version>`),
and record the result here. Rolling back is then a one-line change.

| Version | Status | What changed | Gate result |
|---|---|---|---|
| v1 | **live** | The original prompt: answer briefly, only from the context, say "I do not know" otherwise. | Baseline |
| v2 | candidate | Friendlier persona; "answer by meaning"; "always give a helpful, complete answer". Aimed at the "I do not know" replies to paraphrased questions. | Not run yet (Module 3, Task 3) |
