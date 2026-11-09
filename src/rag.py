"""The agent: retrieval, a versioned prompt, a policy check, and generation.

Module 1 builds the retrieval half (TODO R1-R2), Module 2 the generation
half with a versioned prompt (TODO R3-R4) and the policy check
(TODO R5-R6). rag_answer() at the bottom wires them together
and records what the monitoring in Module 5 needs. It's already written.
"""
import time
from pathlib import Path

import chromadb
import torch
from sentence_transformers import SentenceTransformer
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "chroma_db"
PROMPTS_DIR = ROOT / "prompts"
COLLECTION_NAME = "policies"

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
GENERATOR_MODEL_NAME = "google/flan-t5-base"

# Which prompt in prompts/ is live. Changing it is a release: run the
# quality gate first (Module 3, Task 3) and record the change in prompts/CHANGELOG.md.
PROMPT_VERSION = "v1"

# What the bot says when its policy says not to answer (AGENT_POLICY.md, P3-P4).
REFUSAL_MESSAGE = (
    "I don't have information about that. "
    "For anything else, please contact LumaBox technical support."
)

device = "cuda" if torch.cuda.is_available() else "cpu"


# ------------------------------------------------- Module 1: retrieval
# R1: the same embedding model ingest.py used - a query embedded by a
# different model would be meaningless in this vector space. The collection is
# fetched, not created: building it is ingest.py's job, and failing loudly here
# is better than silently searching an empty index.
embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME, device="cpu")
_client = chromadb.PersistentClient(path=str(DB_PATH))
_collection = _client.get_collection(COLLECTION_NAME)


def retrieve(query, k=2):
    """Return the top-k chunks for a query.

    R2: the query is embedded exactly as the chunks were, including
    normalize_embeddings=True. The collection was created with cosine
    distance, so similarity = 1 - distance. Chroma nests its results one
    level per query, and we only ever send one.

    Returns a list of dicts, best match first, each with "id", "text" and
    "similarity".
    """
    query_vector = embedding_model.encode(query, normalize_embeddings=True).tolist()
    results = _collection.query(query_embeddings=[query_vector], n_results=k)
    return [
        {"id": doc_id, "text": text, "similarity": 1 - distance}
        for doc_id, text, distance in zip(
            results["ids"][0], results["documents"][0], results["distances"][0]
        )
    ]


# ------------------------------------------------- Module 2: generation
# R3: the generator. eval() turns off dropout and the like, so the same prompt
# gives the same answer every time - a precondition for the golden dataset and
# the quality gate meaning anything.
tokenizer = AutoTokenizer.from_pretrained(GENERATOR_MODEL_NAME)
generator = AutoModelForSeq2SeqLM.from_pretrained(GENERATOR_MODEL_NAME).to(device)
generator.eval()


def load_prompt(version):
    """Return the prompt template stored in prompts/answer_<version>.txt."""
    return (PROMPTS_DIR / f"answer_{version}.txt").read_text(encoding="utf-8").strip()


def build_prompt(question, context, version=None):
    """R4: fill the template with the context and the question.

    The template is a file in prompts/, never a string literal in here, so
    that changing the bot's instructions is a reviewable, revertable commit
    and every trace can name the version that produced it.
    """
    template = load_prompt(version or PROMPT_VERSION)
    return template.format(context=context, question=question)


def generate_answer(prompt):
    """R4: run the model on the prompt and return its answer as text.

    truncation=False on purpose: silently cutting the prompt would drop the
    end of the retrieved context and produce a confidently wrong answer with
    nothing in the trace to explain it. Failing loudly makes the 512-token
    budget a visible engineering constraint on k and chunk size instead.

    do_sample=False makes generation greedy, so the answer is reproducible.
    """
    inputs = tokenizer(prompt, return_tensors="pt", truncation=False).to(device)
    token_count = inputs["input_ids"].shape[1]
    if token_count > 512:
        raise ValueError(
            f"Prompt is {token_count} tokens, over flan-t5's 512 token budget. "
            "Reduce k or passage length."
        )
    with torch.inference_mode():
        output = generator.generate(**inputs, max_new_tokens=64, do_sample=False)
    return tokenizer.decode(output[0], skip_special_tokens=True)


# ------------------------------------------------- Module 2: policy
# R5: chosen from the scores measured in Module 1, Task 3, not guessed.
#   lowest in-scope question         0.42  ("When will I get my money back?")
#   highest clearly out-of-scope     0.10  ("Can you recommend a good restaurant?")
# 0.30 sits roughly in the middle of that gap: it leaves ~0.12 of headroom
# under the worst fair question, so a reworded one does not get refused, and
# ~0.20 of margin over unrelated questions. It cannot separate the "tricky"
# out-of-scope questions, which score 0.42-0.47 because they share vocabulary
# with the policies - that is the documented gap under P6, not a bad threshold.
SIMILARITY_THRESHOLD = 0.30


def should_refuse(hits):
    """AGENT_POLICY.md P1: refuse when nothing retrieved is relevant enough.

    R6: refuse when nothing came back at all, or when even the best match is
    below SIMILARITY_THRESHOLD. This lives in code rather than in the prompt
    so that a prompt change cannot remove it: Module 2, Task 2 showed prompt
    v2 happily answering "What's the weather like today?" with "8:00 and
    17:00" when the only rule was a sentence in the prompt.
    """
    return not hits or hits[0]["similarity"] < SIMILARITY_THRESHOLD


# ------------------------------------------------- the agent
def kb_version():
    """Which version of the knowledge base is being searched (set by ingest.py)."""
    return (_collection.metadata or {}).get("kb_version", "unknown")


def rag_answer(question, k=2, search_query=None, enforce_policy=True, prompt_version=None):
    """Answer a question and return everything a trace needs.

    enforce_policy=False skips the policy check (Module 2, Task 2 compares both).
    prompt_version overrides PROMPT_VERSION (the quality gate uses it).
    """
    version = prompt_version or PROMPT_VERSION
    started = time.perf_counter()
    hits = retrieve(search_query or question, k)
    retrieved = time.perf_counter()

    result = {
        "question": question,
        "hits": hits,
        "refused": False,
        "context": "",
        "prompt": None,
        "prompt_version": version,
        "kb_version": kb_version(),
        "models": {"embedding": EMBEDDING_MODEL_NAME, "generator": GENERATOR_MODEL_NAME},
    }
    if enforce_policy and should_refuse(hits):
        # Deterministic: the generator is never called.
        result.update(answer=REFUSAL_MESSAGE, refused=True)
    else:
        context = "\n".join(h["text"] for h in hits)
        prompt = build_prompt(question, context, version)
        result.update(context=context, prompt=prompt, answer=generate_answer(prompt))

    finished = time.perf_counter()
    result["timings_ms"] = {
        "retrieve": round((retrieved - started) * 1000),
        "generate": round((finished - retrieved) * 1000),
    }
    return result
