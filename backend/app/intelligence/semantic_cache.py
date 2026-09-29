"""
semantic_cache.py
Owner: Language Brain (Kavyansh)

Caches the STRUCTURED intelligence result, keyed by embedding similarity.

Safety design (handoff section 27):
A hit requires BOTH
  1. query embedding similarity to a cached entry >= threshold, AND
  2. the current retrieval top-1 scenario_id == the cached entry's top-1.
Condition 2 is the guard against "semantically close but different
problem" collisions (e.g. overheating vs fast drain).

NOTE: MiniLM-style models give low absolute cosine scores for true
paraphrases (~0.5-0.7), so the threshold must be tuned on real data
with the benchmark - do not assume 0.90.
"""

import copy
import os
import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from . import embeddings

SEMANTIC_CACHE_THRESHOLD = float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.51"))
CATALOG_VERSION = os.getenv("CATALOG_VERSION", "test-v1")
EMBEDDING_VERSION = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")


@dataclass
class CacheEntry:
    embedding: np.ndarray
    top_scenario_id: str
    result: dict
    catalog_version: str
    embedding_version: str
    created_at: float = field(default_factory=time.time)


@dataclass
class CacheMetrics:
    hits: int = 0
    misses: int = 0
    false_hit_rejections: int = 0  # similar enough, but retrieval top-1 disagreed

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0


class SemanticCache:
    def __init__(self, threshold: float = SEMANTIC_CACHE_THRESHOLD):
        self.threshold = threshold
        self._entries: list[CacheEntry] = []
        self.metrics = CacheMetrics()

    def lookup(self, query_embedding: np.ndarray,
               top_scenario_id: Optional[str]) -> Optional[dict]:
        start = time.time()
        best_entry, best_sim = None, -1.0

        if top_scenario_id:  # no retrieval agreement possible -> always miss
            for entry in self._entries:
                if (entry.catalog_version != CATALOG_VERSION
                        or entry.embedding_version != EMBEDDING_VERSION):
                    continue  # stale entry
                sim = embeddings.cosine_similarity(query_embedding, entry.embedding)
                if sim < self.threshold:
                    continue
                if entry.top_scenario_id != top_scenario_id:
                    self.metrics.false_hit_rejections += 1
                    continue
                if sim > best_sim:
                    best_sim, best_entry = sim, entry

        lookup_ms = int((time.time() - start) * 1000)

        if best_entry is None:
            self.metrics.misses += 1
            return None

        self.metrics.hits += 1
        result = copy.deepcopy(best_entry.result)  # never mutate the stored entry
        result.setdefault("metadata", {})
        result["metadata"].update({
            "cache_hit": True,
            "cache_similarity": round(best_sim, 3),
            "cache_lookup_ms": lookup_ms,
            "llm_call_avoided": True,
        })
        return result

    def store(self, query_embedding: np.ndarray, top_scenario_id: str, result: dict) -> None:
        self._entries.append(CacheEntry(
            embedding=query_embedding,
            top_scenario_id=top_scenario_id,
            result=copy.deepcopy(result),
            catalog_version=CATALOG_VERSION,
            embedding_version=EMBEDDING_VERSION,
        ))

    def size(self) -> int:
        return len(self._entries)


if __name__ == "__main__":
    cache = SemanticCache()
    fake = {"candidates": [{"scenario_id": "BATTERY_FAST_DRAIN", "confidence": 0.9}], "metadata": {}}

    e1 = embeddings.embed_text("my battery dies very quickly")
    print("1st (expect MISS):", cache.lookup(e1, "BATTERY_FAST_DRAIN"))
    cache.store(e1, "BATTERY_FAST_DRAIN", fake)

    e2 = embeddings.embed_text("my phone loses charge crazy fast")
    print("2nd paraphrase, same top-1 (expect HIT):", cache.lookup(e2, "BATTERY_FAST_DRAIN") is not None)
    print("3rd similar but retrieval says HEATING (expect MISS):", cache.lookup(e2, "BATTERY_HEATING"))
    e4 = embeddings.embed_text("my camera is blurry")
    print("4th unrelated (expect MISS):", cache.lookup(e4, "CAMERA_FOCUS_ISSUE"))
    print("Metrics:", cache.metrics)
