# Module 4 — Deployment: CI/CD (reading notes)

My written answers for Module 4, Tasks 1 and 2. Task 3 (running the Streamlit
front end) is recorded at the bottom.

## Task 1 — The Dockerfile and the pipeline

### Why are the model weights downloaded when the image is *built*?

So that starting a container is instant and deterministic. If the weights were
fetched at start-up, every container would pull ~1 GB from Hugging Face before
it could answer anything: slow, dependent on the network, and dependent on a
third party still serving that exact revision. Baking them in makes the image
self-contained — the `ENV HF_HUB_OFFLINE=1` at the bottom of the Dockerfile
then guarantees that runtime never reaches the network for a model at all. Two
containers from the same image also provably hold the same weights, which is
what makes an answer reproducible from its image tag.

### Why is `requirements.txt` installed before the code is copied?

Docker caches each instruction as a layer and reuses every layer up to the
first one whose inputs changed. Libraries change rarely; `src/` changes on
every commit. Copying `requirements.txt` and installing first means a normal
code change invalidates only the last few cheap layers (`COPY src/`, `RUN
python -m src.ingest`) and reuses the expensive pip install and the model
download. Copying the whole project first would re-run both on every commit.

### Which job runs only for changes pushed to `main`?

`deploy`. Its condition is
`if: github.ref == 'refs/heads/main' && github.event_name == 'push'`, so a pull
request runs `test` and `build` and then stops. It also names
`environment: production`, which is where GitHub can require a human approval
before the rollout step runs.

### The three jobs, in order

`test` → `build` → `deploy`, chained by `needs:`, so a failure stops everything
downstream.

The `test` job's steps map onto the commands from today's class:

| CI step | Command | What it protects |
|---|---|---|
| Build the knowledge base | `python -m src.ingest` | The index is rebuilt from the committed documents, never copied from a laptop |
| Unit and golden tests | `pytest` | Retrieval and the policy decision — the deterministic parts, must be 100% |
| Quality gate | `python -m src.gate` | Generated answers against `tests/gate_baseline.json`; a non-zero exit fails the job |

## Task 2 — Tracing four changes through the pipeline

### A. A teammate sets `PROMPT_VERSION = "v2"` and pushes to `main`

Stopped by the **Quality gate** step of `test`. Module 3, Task 3 measured v2:
`out of scope` drops 6/6 → 3/6 and `refund` 3/3 → 2/3, so `src/gate.py` exits 1
and the job fails. `build` and `deploy` never start, no new image is produced,
and customers keep running the v1 image. This is the step that turns "it felt
better" into a release decision.

### B. Someone deletes "24/7" from `data/lumabox_policies.txt` by accident

Stopped by **`pytest`** in the same job. The three `support_hours` golden rows
assert that the retrieved chunks contain `24/7`, and
`tests/test_retrieval.py::test_retrieve_finds_relevant_passage` asserts the
same thing directly, so all four fail. The point is that a change to the
*knowledge* is gated exactly like a change to the code: it is a commit, it goes
through the same pipeline, and `KB_VERSION` changes with it so every later
trace says which text produced it.

### C. A typo fix in `README.md`

Nothing stops it. `test` passes (the README is not an input to retrieval),
`build` produces a new image tagged with the commit SHA, and on `main` `deploy`
ships it — possibly after the manual approval the `production` environment can
require. The new image is functionally identical to the old one; the cost of
shipping it anyway is that every deployment comes from the pipeline and nothing
is ever edited on the server.

### D. v1 is live, and a week later it fails on a new kind of question

Nothing in the pipeline catches this, because the pipeline only knows the tests
it was given — which is why Module 5 exists. The loop is: find it in the traces,
add the new wordings to `tests/golden.xlsx` and watch them *fail*, then fix the
cause where it actually lives (the documents for a knowledge gap, a new prompt
version for a generation error, the threshold or a policy rule for a bad refusal
decision), then push it through `test` → `build` → `deploy`. If the fix itself
turns out to be bad, rolling back means redeploying the previous image by its
commit tag, not patching the running container. Nothing is ever fixed by hand in
production, because a hand-fix is invisible to the next deployment and would be
overwritten by it.

## Task 3 — Running the web interface

`streamlit run app.py` serves the same bot at <http://localhost:8501>. The page
gives the same answers and the same refusals as `python -m src.main`, because
`app.py` calls the same `rag_answer()` — the UI is a front end, not a second
implementation of the agent. The first answer takes roughly 20 seconds while the
embedding model and flan-t5 load; later answers are fast. This is the same
command the container's `CMD` runs, which is why what is tested locally is what
production serves.
