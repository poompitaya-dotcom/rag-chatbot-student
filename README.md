# RAG Chatbot - Starter

Local, offline RAG chatbot over a small set of fictional LumaBox support
policies (`sentence-transformers/all-MiniLM-L6-v2` for embeddings,
`google/flan-t5-base` for generation, Chroma as the vector database),
built the way AI engineers run it for real: a persistent knowledge base, a
versioned prompt, an enforced policy, a golden dataset with a quality gate,
a CI/CD pipeline, and tracing for continuous monitoring.

Look for `TODO` comments (`git grep -n TODO`, or search in VS Code):
`I1-I4` in `src/ingest.py`, `R1-R6` in `src/rag.py`, `T1` in
`tests/test_retrieval.py`, and `T2` (rows for `tests/golden.xlsx`) in
`tests/test_golden.py`. Everything else is already written.

## Before class

You need VS Code (with the Python extension), Python 3.11-3.13, and git.
Then, from this folder:

```
python -m venv .venv
```

Windows (PowerShell):
```
.venv\Scripts\activate
```
Mac/Linux:
```
source .venv/bin/activate
```

Then:
```
pip install -r requirements.txt
python setup_check.py
```

`setup_check.py` downloads the two models (~1.1 GB, once) and confirms
everything loads. In class, `python setup_check.py --offline` proves nothing
needs downloading.

## Run (once the TODOs are filled in)

Always run from the project folder, as a module (`python -m ...`). VS Code's
Run button runs the file as a loose script and fails with
`No module named 'src'`.

| Command | What it does |
|---|---|
| `python -m src.ingest` | Build the knowledge base (re-run when documents change) |
| `python -m src.main` | Chat in the terminal; every turn is traced to `logs/` |
| `python -m src.scores` | Top retrieval similarity for some questions |
| `python -m src.policy_demo` | Compare answers with and without the policy |
| `pytest` | Unit and golden dataset tests (must all pass) |
| `python -m src.gate` | Quality gate: generated answers vs the baseline |
| `python -m src.review` | Review traces: flags, a random sample, sentiment |
| `streamlit run app.py` | The web front end the production container runs |

## Project layout

```
rag-chatbot/
├── data/lumabox_policies.txt      # the knowledge: raw policy text
├── src/ingest.py                  # TODO I1-I4: chunk, embed, persist to Chroma
├── src/rag.py                     # TODO R1-R6: retrieval, prompt, policy, agent
├── prompts/                       # versioned prompts + CHANGELOG.md
├── AGENT_POLICY.md                # how the bot must behave, and how that's enforced
├── tests/test_retrieval.py        # TODO T1: one assertion
├── tests/golden.xlsx              # TODO T2: your golden dataset
├── tests/test_golden.py           # runs every golden question
├── src/gate.py                    # quality gate
├── src/main.py, app.py            # CLI and web front end
├── src/monitoring.py, review.py   # tracing and log review
├── src/policy_demo.py             # with vs without policy
├── Dockerfile, .dockerignore      # how production would package the app
├── .github/workflows/ci.yml       # the CI/CD pipeline
├── homework/                      # Homework.md, model_prices.xlsx, traffic.txt
├── setup_check.py                 # pre-class environment check
├── .devcontainer/                 # Codespaces fallback
├── pytest.ini, requirements.txt, .gitignore
└── README.md
```

## Homework

See `homework/Homework.md` in this folder. Submit by zipping this whole
folder, including the `.git` folder, and uploading it to [LMS link].
