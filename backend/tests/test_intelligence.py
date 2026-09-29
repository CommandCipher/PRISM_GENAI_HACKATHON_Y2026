"""
Basic tests for the Language Brain, per handoff doc section 48:
- paraphrase similarity
- ambiguity handling
- retrieval accuracy
- adversarial/hallucination resistance
- cache hit/miss + false-hit safety

Run with: pytest tests/test_intelligence.py -v
(requires Ollama running locally with the configured model pulled)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.intelligence import normalization, embeddings
from app.intelligence.retrieval import ScenarioRetriever
from app.intelligence.semantic_cache import SemanticCache
from app.intelligence import language_brain


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
    assert sim_related > 0.5  # paraphrases should be meaningfully close


def test_retrieval_finds_correct_scenario_in_top_k():
    retriever = ScenarioRetriever()
    results = retriever.search("phone battery draining super fast", top_k=3)
    top_ids = [r.scenario_id for r in results]
    assert "BATTERY_FAST_DRAIN" in top_ids


def test_retrieval_returns_ranked_results():
    retriever = ScenarioRetriever()
    results = retriever.search("my battery dies fast", top_k=3)
    similarities = [r.similarity for r in results]
    assert similarities == sorted(similarities, reverse=True)


def test_cache_miss_then_hit_on_paraphrase():
    cache = SemanticCache()
    e1 = embeddings.embed_text("my battery dies very quickly")
    fake = {"candidates": [{"scenario_id": "BATTERY_FAST_DRAIN", "confidence": 0.9}], "metadata": {}}

    assert cache.lookup(e1, "BATTERY_FAST_DRAIN") is None
    cache.store(e1, "BATTERY_FAST_DRAIN", fake)

    e2 = embeddings.embed_text("my phone loses charge crazy fast")
    hit = cache.lookup(e2, "BATTERY_FAST_DRAIN")
    assert hit is not None
    assert hit["metadata"]["cache_hit"] is True


def test_cache_rejects_when_retrieval_top1_disagrees():
    cache = SemanticCache()
    e1 = embeddings.embed_text("my battery dies very quickly")
    cache.store(e1, "BATTERY_FAST_DRAIN", {"candidates": [], "metadata": {}})

    e2 = embeddings.embed_text("my phone loses charge crazy fast")
    assert cache.lookup(e2, "BATTERY_HEATING") is None  # close text, different scenario
    assert cache.metrics.false_hit_rejections >= 1


def test_cache_does_not_false_hit_across_domains():
    cache = SemanticCache()
    e1 = embeddings.embed_text("my battery dies very quickly")
    cache.store(e1, "BATTERY_FAST_DRAIN", {"candidates": [], "metadata": {}})
    e2 = embeddings.embed_text("my camera photos are blurry")
    assert cache.lookup(e2, "CAMERA_FOCUS_ISSUE") is None


def test_cache_hit_does_not_mutate_stored_entry():
    cache = SemanticCache()
    e1 = embeddings.embed_text("my battery dies very quickly")
    cache.store(e1, "BATTERY_FAST_DRAIN", {"candidates": [], "metadata": {}})
    cache.lookup(e1, "BATTERY_FAST_DRAIN")
    assert "cache_hit" not in cache._entries[0].result["metadata"]


VALID_IDS = {"BATTERY_FAST_DRAIN", "BATTERY_BACKGROUND_USAGE", "BATTERY_HEATING",
             "DISPLAY_NAV_GESTURE_REVERSED", "DISPLAY_FLICKER",
             "CAMERA_FOCUS_ISSUE", "PERFORMANCE_APP_LAG"}


def test_vague_query_returns_no_candidates():
    result = language_brain.analyze("my phone is bad")
    assert result["candidates"] == []
    assert result["complaint_dna"]["ambiguous"] is True


def test_adversarial_query_returns_no_candidates_and_no_invented_ids():
    result = language_brain.analyze("open the secret samsung battery calibration menu")
    assert result["candidates"] == []
    for c in result["candidates"]:
        assert c["scenario_id"] in VALID_IDS


def test_known_complaint_returns_expected_scenario():
    result = language_brain.analyze("swipe gestures go the wrong way after installing an app")
    ids = [c["scenario_id"] for c in result["candidates"]]
    assert "DISPLAY_NAV_GESTURE_REVERSED" in ids


def test_symptoms_come_from_catalog_vocabulary():
    result = language_brain.analyze("my battery dies really fast")
    vocab = {"fast_battery_drain", "background_app_drain", "device_overheating",
             "gesture_direction_reversed", "screen_flicker",
             "camera_focus_failure", "post_update_slowdown"}
    assert set(result["complaint_dna"]["symptoms"]) <= vocab


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
