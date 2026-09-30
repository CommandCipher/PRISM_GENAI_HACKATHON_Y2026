"""Language Brain tests against the supplied Theme 2 SIIS starter dataset."""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.intelligence import embeddings, language_brain, normalization
from app.intelligence.retrieval import ScenarioRetriever
from app.intelligence.semantic_cache import SemanticCache

def test_normalization_preserves_meaning():
    result = normalization.normalize_query("battery's trash rn!!!")
    assert "battery" in result
    assert "trash" in result

def test_normalization_handles_empty():
    assert normalization.normalize_query("") == ""
    assert normalization.normalize_query("   ") == ""

def test_paraphrase_similarity_is_high():
    a = embeddings.embed_text("My battery dies really fast")
    b = embeddings.embed_text("My phone loses charge insanely quickly")
    c = embeddings.embed_text("My camera won't focus")
    sim_related = embeddings.cosine_similarity(a, b)
    sim_unrelated = embeddings.cosine_similarity(a, c)
    assert sim_related > sim_unrelated
    assert sim_related > 0.5

def test_retrieval_finds_real_blank_screen_scenario():
    retriever = ScenarioRetriever()
    results = retriever.search("my phone screen is completely blank and black", top_k=3)
    top_ids = [result.scenario_id for result in results]
    assert set(top_ids) & {"row_2", "row_4", "row_13", "row_15", "row_22"}

def test_retrieval_returns_ranked_results():
    retriever = ScenarioRetriever()
    results = retriever.search("my screen is completely blank", top_k=3)
    similarities = [result.similarity for result in results]
    assert similarities == sorted(similarities, reverse=True)

def test_cache_miss_then_hit_on_paraphrase():
    cache = SemanticCache()
    e1 = embeddings.embed_text("my battery dies very quickly")
    fake = {"candidates": [{"scenario_id": "row_2", "confidence": 0.9}], "metadata": {}}
    assert cache.lookup(e1, "row_2") is None
    cache.store(e1, "row_2", fake)
    e2 = embeddings.embed_text("my phone loses charge crazy fast")
    hit = cache.lookup(e2, "row_2")
    assert hit is not None
    assert hit["metadata"]["cache_hit"] is True

def test_cache_rejects_when_retrieval_top1_disagrees():
    cache = SemanticCache()
    e1 = embeddings.embed_text("my battery dies very quickly")
    cache.store(e1, "row_2", {"candidates": [], "metadata": {}})
    e2 = embeddings.embed_text("my phone loses charge crazy fast")
    assert cache.lookup(e2, "row_21") is None
    assert cache.metrics.false_hit_rejections >= 1

def test_cache_does_not_false_hit_across_domains():
    cache = SemanticCache()
    e1 = embeddings.embed_text("my battery dies very quickly")
    cache.store(e1, "row_2", {"candidates": [], "metadata": {}})
    e2 = embeddings.embed_text("my screen is cracked")
    assert cache.lookup(e2, "row_14") is None

def test_cache_hit_does_not_mutate_stored_entry():
    cache = SemanticCache()
    e1 = embeddings.embed_text("my battery dies very quickly")
    cache.store(e1, "row_2", {"candidates": [], "metadata": {}})
    cache.lookup(e1, "row_2")
    assert "cache_hit" not in cache._entries[0].result["metadata"]

def test_vague_query_returns_no_candidates():
    result = language_brain.analyze("my phone is bad")
    assert result["candidates"] == []
    assert result["complaint_dna"]["ambiguous"] is True

def test_adversarial_query_returns_no_candidates_and_no_invented_ids():
    result = language_brain.analyze("open the secret samsung battery calibration menu")
    assert result["candidates"] == []
    for candidate in result["candidates"]:
        assert candidate["scenario_id"].startswith("row_")

def test_known_real_complaint_returns_real_scenario():
    result = language_brain.analyze("my phone screen is completely black and will not turn on")
    ids = [candidate["scenario_id"] for candidate in result["candidates"]]
    assert ids
    assert any(scenario_id in ids for scenario_id in {"row_2", "row_4", "row_13", "row_15", "row_22"})
    assert all(scenario_id.startswith("row_") for scenario_id in ids)

def test_symptoms_never_invented_from_old_synthetic_vocabulary():
    result = language_brain.analyze("my screen is completely blank")
    # The real SIIS records currently do not provide a symptoms field, so
    # the LLM receives an empty allowed-symptom vocabulary.
    assert result["complaint_dna"]["symptoms"] == []

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
