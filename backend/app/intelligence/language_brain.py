"""
language_brain.py
Owner: Language Brain (Kavyansh)

Entry point for the Device Brain:   result = analyze(query)

Pipeline:
  normalize -> embed once -> retrieve top-K (cheap, ~20ms)
    -> GATE: top retrieval similarity too low  => no match, LLM never called
    -> semantic cache lookup (needs similarity AND same retrieval top-1)
    -> LLM interprets + endorses candidates (can only pick supplied IDs)
    -> re-rank, calibrate confidence, return

Ends at candidate scenario IDs. Never produces deeplinks/actions/steps.
"""

import os
import time
from typing import Optional
import copy

from . import normalization, embeddings, ranking, telemetry
from .retrieval import ScenarioRetriever
from .semantic_cache import SemanticCache
from .llm import LLMClient

TOP_K = int(os.getenv("TOP_K", "3"))
# Below this raw retrieval similarity the query is treated as "no known scenario"
# (vague like "my phone is bad", or adversarial like "secret menu"). Tune with benchmark.
MIN_RETRIEVAL_SIMILARITY = float(os.getenv("MIN_RETRIEVAL_SIMILARITY", "0.55"))
MIN_ACCEPTABLE_CONFIDENCE = 0.35


class LanguageBrain:
    def __init__(self, warmup: bool = True):
        self.retriever = ScenarioRetriever()
        self.cache = SemanticCache()
        self.llm = LLMClient()
        if warmup:
            self.llm.warmup()

    def fast_lookup(self, raw_query: str) -> Optional[dict]:
        """Run only the cheap embedding/retrieval/cache path.

        This intentionally never calls the LLM. It is used by the Device Brain
        before the expensive reasoning path so a previously validated semantic
        query can complete end-to-end without an LLM call.
        """
        t_start = time.time()
        normalized = normalization.normalize_query(raw_query)
        if not normalized:
            return None

        t = time.time()
        query_vec = embeddings.embed_text(normalized)
        embed_ms = int((time.time() - t) * 1000)

        t = time.time()
        raw_candidates = self.retriever.search_vec(query_vec, top_k=TOP_K)
        retrieval_ms = int((time.time() - t) * 1000)

        if not raw_candidates or raw_candidates[0].similarity < MIN_RETRIEVAL_SIMILARITY:
            return None

        cached = self.cache.lookup(query_vec, raw_candidates[0].scenario_id)
        if cached is None:
            return None

        result = copy.deepcopy(cached)
        result["complaint_dna"]["raw_query"] = raw_query
        result["metadata"]["retrieval_latency_ms"] = retrieval_ms
        result["metadata"]["embedding_latency_ms"] = embed_ms
        result["metadata"]["llm_latency_ms"] = 0
        result["metadata"]["llm_call_avoided"] = True
        result["metadata"]["fast_path"] = True
        result["metadata"]["total_latency_ms"] = int((time.time() - t_start) * 1000)
        telemetry.record_cache_hit(result["metadata"].get("cache_lookup_ms", 0))
        return result

    def analyze(self, raw_query: str) -> dict:
        t_start = time.time()

        normalized = normalization.normalize_query(raw_query)
        if not normalized:
            return self._no_match(raw_query, "", "empty_query", t_start)

        t = time.time()
        query_vec = embeddings.embed_text(normalized)
        embed_ms = int((time.time() - t) * 1000)

        t = time.time()
        raw_candidates = self.retriever.search_vec(query_vec, top_k=TOP_K)
        retrieval_ms = int((time.time() - t) * 1000)

        # ---- GATE: nothing in the catalog is close enough ----
        if not raw_candidates or raw_candidates[0].similarity < MIN_RETRIEVAL_SIMILARITY:
            telemetry.record_cache_miss(retrieval_ms=retrieval_ms, llm_ms=0)
            return self._no_match(raw_query, normalized, "low_retrieval_similarity", t_start,
                                  retrieval_ms=retrieval_ms, embed_ms=embed_ms)

        top_id = raw_candidates[0].scenario_id

        # ---- Semantic cache (similarity + retrieval agreement) ----
        cached = self.cache.lookup(query_vec, top_id)
        if cached is not None:
            cached["metadata"]["retrieval_latency_ms"] = retrieval_ms
            cached["metadata"]["embedding_latency_ms"] = embed_ms
            cached["metadata"]["total_latency_ms"] = int((time.time() - t_start) * 1000)
            cached["complaint_dna"]["raw_query"] = raw_query  # keep the CURRENT user's wording
            telemetry.record_cache_hit(cached["metadata"].get("cache_lookup_ms", 0))
            return cached

        # ---- LLM reasoning (cache miss) ----
        payload = []
        for c in raw_candidates:
            scen = self.retriever.get_scenario(c.scenario_id) or {}
            payload.append({
                "scenario_id": c.scenario_id,
                "description": c.description,
                "similarity": c.similarity,
                "symptoms": scen.get("symptoms", []),
            })

        t = time.time()
        llm_result = self.llm.generate_structured(normalized, payload)
        llm_ms = int((time.time() - t) * 1000)

        prelim = ranking.rank_candidates(raw_candidates)

        if not llm_result.success:
            # Fallback: retrieval-only, never crash (handoff section 46).
            result = self._build_result(raw_query, normalized, prelim[0].domain, [],
                                        prelim[0].confidence, prelim,
                                        retrieval_ms, embed_ms, llm_ms, 0,
                                        llm_error=llm_result.error)
            telemetry.record_cache_miss(retrieval_ms, llm_ms, llm_failed=True)
            result["metadata"]["total_latency_ms"] = int((time.time() - t_start) * 1000)
            return result  # not cached: it wasn't LLM-validated

        telemetry.record_cache_miss(retrieval_ms, llm_ms, tokens=llm_result.total_tokens)

        # LLM said "none of these fit" -> respect it. No fallback to raw retrieval.
        if not llm_result.ranked_scenario_ids:
            res = self._no_match(raw_query, normalized, "llm_rejected_all_candidates", t_start,
                                 retrieval_ms=retrieval_ms, embed_ms=embed_ms, llm_ms=llm_ms)
            res["complaint_dna"]["domain"] = llm_result.domain
            return res

        final_ranked = ranking.rank_candidates(
            raw_candidates,
            inferred_domain=llm_result.domain,
            inferred_symptoms=llm_result.symptoms,
            scenario_lookup=self.retriever.get_scenario,
        )
        endorsed = set(llm_result.ranked_scenario_ids)
        final_ranked = [r for r in final_ranked if r.scenario_id in endorsed]

        # Conservative confidence: never higher than either signal alone.
        llm_conf = llm_result.confidence or final_ranked[0].confidence
        confidence = min(llm_conf, final_ranked[0].confidence)

        result = self._build_result(raw_query, normalized, llm_result.domain,
                                    llm_result.symptoms, confidence, final_ranked,
                                    retrieval_ms, embed_ms, llm_ms, llm_result.total_tokens,
                                    temporal=llm_result.temporal_pattern,
                                    entities=llm_result.entities)
        result["metadata"]["total_latency_ms"] = int((time.time() - t_start) * 1000)

        # Only cache confident, unambiguous, LLM-validated results.
        if not result["complaint_dna"]["ambiguous"] and result["candidates"]:
            self.cache.store(query_vec, top_id, result)
        return result

    # ------------------------------------------------------------------
    def _build_result(self, raw_query, normalized, domain, symptoms, confidence,
                      ranked, retrieval_ms, embed_ms, llm_ms, llm_tokens,
                      llm_error=None, temporal=None, entities=None) -> dict:
        ambiguous = ranking.is_ambiguous(ranked)
        if ambiguous:
            cands = ranked[:2]  # surface top-2; Device Brain / confidence gate decides
        else:
            cands = [r for r in ranked if r.confidence >= MIN_ACCEPTABLE_CONFIDENCE]
        return {
            "complaint_dna": {
                "raw_query": raw_query,
                "domain": domain,
                "symptoms": symptoms,
                "entities": entities or {},
                "temporal_pattern": temporal,
                "severity": None,
                "canonical_query": normalized,
                "confidence": round(confidence, 3),
                "ambiguous": ambiguous,
            },
            "candidates": [
                {"scenario_id": c.scenario_id,
                 "retrieval_similarity": round(c.retrieval_similarity, 3),
                 "confidence": round(c.confidence, 3)}
                for c in cands
            ],
            "metadata": {
                "cache_hit": False,
                "embedding_latency_ms": embed_ms,
                "retrieval_latency_ms": retrieval_ms,
                "llm_latency_ms": llm_ms,
                "llm_tokens": llm_tokens,
                "llm_error": llm_error,
            },
        }

    def _no_match(self, raw_query, normalized, reason, t_start, **meta) -> dict:
        return {
            "complaint_dna": {
                "raw_query": raw_query, "domain": None, "symptoms": [], "entities": {},
                "temporal_pattern": None, "severity": None,
                "canonical_query": normalized, "confidence": 0.0, "ambiguous": True,
            },
            "candidates": [],
            "metadata": {"cache_hit": False, "reason": reason,
                         "total_latency_ms": int((time.time() - t_start) * 1000), **meta},
        }


_brain: Optional[LanguageBrain] = None


def _get_brain(warmup: bool = True) -> LanguageBrain:
    global _brain
    if _brain is None:
        _brain = LanguageBrain(warmup=warmup)
    return _brain


def fast_lookup(raw_query: str) -> Optional[dict]:
    """Cheap semantic-cache probe; never invokes the LLM."""
    if _brain is None:
        return None
    return _brain.fast_lookup(raw_query)


def analyze(raw_query: str) -> dict:
    return _get_brain(warmup=True).analyze(raw_query)


if __name__ == "__main__":
    import json
    for q in [
        "my battery dies really fast",
        "phone loses charge insanely quickly",   # expect CACHE HIT
        "battery drains like crazy these days",  # expect CACHE HIT
        "swipe gestures go the wrong way after installing an app",
        "phone gets super hot and battery drops",  # must NOT hit the fast-drain cache entry
        "my phone is bad",                        # expect no match, no LLM call
        "open the secret samsung battery calibration menu",  # expect no match
    ]:
        r = analyze(q)
        m = r["metadata"]
        print(f"\n{q!r}\n  candidates={[c['scenario_id'] for c in r['candidates']]} "
              f"conf={r['complaint_dna']['confidence']} ambiguous={r['complaint_dna']['ambiguous']}\n"
              f"  cache_hit={m.get('cache_hit')} reason={m.get('reason')} "
              f"total_ms={m.get('total_latency_ms')} llm_ms={m.get('llm_latency_ms')}")
        if m.get("llm_error"):
               print(f"  !!! LLM ERROR: {m['llm_error']}")
    telemetry.print_summary()
