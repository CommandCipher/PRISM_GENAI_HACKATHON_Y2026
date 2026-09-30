from __future__ import annotations
# Semantic cache for validated Language Brain intelligence results.
import copy, os, time
from dataclasses import dataclass, field
from typing import Optional
import numpy as np
from . import embeddings

SEMANTIC_CACHE_THRESHOLD = float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.51"))
CATALOG_VERSION = os.getenv("CATALOG_VERSION", "siis-v1")
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
    false_hit_rejections: int = 0
    @property
    def hit_rate(self): return self.hits / (self.hits + self.misses) if self.hits + self.misses else 0.0

class SemanticCache:
    def __init__(self, threshold: float = SEMANTIC_CACHE_THRESHOLD):
        self.threshold=threshold
        self._entries=[]
        self.metrics=CacheMetrics()

    def lookup(self, query_embedding: np.ndarray, top_scenario_id: Optional[str]):
        start=time.time()
        best=None; best_sim=-1.0
        if top_scenario_id:
            for entry in self._entries:
                if entry.catalog_version != CATALOG_VERSION or entry.embedding_version != EMBEDDING_VERSION:
                    continue
                sim=embeddings.cosine_similarity(query_embedding, entry.embedding)
                if sim < self.threshold:
                    continue
                if entry.top_scenario_id != top_scenario_id:
                    self.metrics.false_hit_rejections += 1
                    continue
                if sim > best_sim:
                    best_sim=sim; best=entry
        lookup_ms=int((time.time()-start)*1000)
        if best is None:
            self.metrics.misses += 1
            return None
        self.metrics.hits += 1
        result=copy.deepcopy(best.result)
        result.setdefault("metadata", {}).update({
            "cache_hit": True,
            "cache_similarity": round(best_sim,3),
            "cache_lookup_ms": lookup_ms,
            "llm_call_avoided": True,
        })
        return result

    def store(self, query_embedding: np.ndarray, top_scenario_id: str, result: dict):
        self._entries.append(CacheEntry(
            embedding=query_embedding,
            top_scenario_id=top_scenario_id,
            result=copy.deepcopy(result),
            catalog_version=CATALOG_VERSION,
            embedding_version=EMBEDDING_VERSION,
        ))
