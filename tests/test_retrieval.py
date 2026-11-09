"""Verification test: check the retrieval step, not the model's wording.

The generator's exact phrasing can vary between runs; retrieval over a
fixed, small document set should not. This is what "testing an AI system"
usually means in practice - verify the deterministic scaffolding around the
model, not the model's free-text output.

Note: chunk ids are generic (chunk_0, chunk_1, ...) since they came from
splitting raw text, not from hand-labeled documents - so these tests check
retrieved *content*, not a specific id.

Run from the project folder with:
    pytest
"""
from src.rag import retrieve


def test_retrieve_returns_requested_number_of_hits():
    hits = retrieve("How do I return an item?", k=2)
    assert len(hits) == 2


def test_retrieve_finds_relevant_passage():
    hits = retrieve("Is technical support available on weekends?", k=2)
    # TODO T1: assert that one of the retrieved chunks actually contains the
    # expected fact ("24/7"). Check the chunk's *text*, not its id.
    assert ...
