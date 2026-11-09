"""Build the local Chroma index from data/lumabox_policies.txt.

Unlike a clean JSON array, this is one raw text file - real documents
usually arrive this way. You have to decide how to split it into
retrievable pieces before you can embed anything.

Run this once (and again any time the documents change):
    python -m src.ingest
"""
import hashlib
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "lumabox_policies.txt"
DB_PATH = Path(__file__).resolve().parent.parent / "chroma_db"
COLLECTION_NAME = "policies"

# A short fingerprint of the source text. It changes whenever the documents
# change, and every answer logs it, so a wrong answer can be traced back to
# the exact knowledge it came from.
KB_VERSION = hashlib.sha256(DATA_PATH.read_bytes()).hexdigest()[:12]

# I1: the embedding model. Pinned by name so the index side (here) and the
# query side (src/rag.py) always share one vector space; device="cpu" keeps the
# result reproducible on any machine, including the CI runner.
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME, device="cpu")


def chunk_documents():
    """Split the raw policy text into a list of chunk strings.

    I2: the file holds one policy per blank-line-separated block, and each
    block is a heading followed by its body. The file's own title
    ("LumaBox Customer Policies") is a heading with no body, so after
    stripping it contains no newline - that is what tells it apart from a
    real policy chunk.
    """
    text = DATA_PATH.read_text(encoding="utf-8")
    raw_chunks = [chunk.strip() for chunk in text.split("\n\n")]
    return [chunk for chunk in raw_chunks if "\n" in chunk]


def build_index():
    chunks = chunk_documents()

    # I3: a persistent client, so the index survives a restart. The old
    # collection is dropped first, which makes re-running ingest idempotent
    # instead of additive. KB_VERSION goes into the collection metadata,
    # which is where src/rag.py reads it from for every trace.
    client = chromadb.PersistentClient(path=str(DB_PATH))
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass  # first run: there is no old collection to delete
    collection = client.create_collection(
        COLLECTION_NAME,
        metadata={"hnsw:space": "cosine", "kb_version": KB_VERSION},
    )

    # I4: embed with the same normalisation the query side uses, and give the
    # chunks generic ids - they came from splitting raw text, not from
    # pre-labelled documents.
    embeddings = embedding_model.encode(chunks, normalize_embeddings=True).tolist()
    ids = [f"chunk_{i}" for i in range(len(chunks))]
    collection.add(ids=ids, documents=chunks, embeddings=embeddings)

    print(f"Indexed {len(chunks)} chunks into {DB_PATH} (kb_version {KB_VERSION})")


if __name__ == "__main__":
    build_index()
