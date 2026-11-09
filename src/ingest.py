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
import pandas as pd
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "lumabox_policies.txt"
PRICES_PATH = ROOT / "homework" / "model_prices.xlsx"
DB_PATH = ROOT / "chroma_db"
COLLECTION_NAME = "policies"

# A short fingerprint of the source documents. It changes whenever the
# knowledge changes, and every answer logs it, so a wrong answer can be traced
# back to the exact knowledge it came from. The price table is hashed in too
# (homework Exercise 1): a price change is a knowledge change, so it must be
# visible in the traces exactly like a policy change.
KB_VERSION = hashlib.sha256(
    DATA_PATH.read_bytes() + PRICES_PATH.read_bytes()
).hexdigest()[:12]

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


def price_documents():
    """One sentence per row of homework/model_prices.xlsx (Exercise 1).

    A table cell is not a retrievable unit: the embedding model was trained on
    sentences, and "4990" on its own carries no meaning to match a question
    against. So each row becomes a sentence that contains both the way the
    product is named and its price.

    The model column is messy on purpose - serial code and product name run
    together, e.g. "LMX-201 LumaBox X100" - and it is kept verbatim, so a
    customer who quotes either one has something to match.
    """
    table = pd.read_excel(PRICES_PATH)
    return [
        f"The {str(row.model).strip()} costs {int(row.price)} THB."
        for row in table.itertuples(index=False)
    ]


def build_index():
    chunks = chunk_documents()
    prices = price_documents()

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
    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=[{"source": "policy"}] * len(chunks),
    )

    # Exercise 1: the prices go into the SAME collection, tagged by source.
    # One index means one retrieval path: no "does this look like a price
    # question?" router deciding where to search, which would be a second
    # place for the bot to be wrong and would have to be tested separately.
    # The source metadata is for provenance and filtering, not routing.
    price_embeddings = embedding_model.encode(prices, normalize_embeddings=True).tolist()
    price_ids = [f"price_{i}" for i in range(len(prices))]
    collection.add(
        ids=price_ids,
        documents=prices,
        embeddings=price_embeddings,
        metadatas=[{"source": "price"}] * len(prices),
    )

    print(
        f"Indexed {len(chunks)} policy chunks and {len(prices)} price rows "
        f"into {DB_PATH} (kb_version {KB_VERSION})"
    )


if __name__ == "__main__":
    build_index()
