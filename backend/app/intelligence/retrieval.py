"""
retrieval.py
Language Brain retrieval over the supplied SIIS starter dataset.
"""

import json
import os
import re
from dataclasses import dataclass
from typing import List

import numpy as np

from . import embeddings

DEFAULT_TOP_K = int(os.getenv("TOP_K", "3"))
DEFAULT_DATASET_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "siis_responses.json"
)

DOMAIN_TERMS = {
    "display": ("screen", "display", "touchscreen", "rotate", "mirroring", "multi window"),
    "camera": ("camera", "flicker", "photo", "focus"),
    "performance": ("performance", "app", "slow", "lag", "safe mode"),
    "battery": ("battery", "charge", "charging", "power saving"),
}

@dataclass
class Candidate:
    scenario_id: str
    domain: str
    description: str
    similarity: float

class ScenarioRetriever:
    def __init__(self, dataset_path: str = DEFAULT_DATASET_PATH):
        self.dataset_path = dataset_path
        self._scenarios = []
        self._scenario_ids = []
        self._index = None
        self._load_and_build()

    def _domain(self, record: dict) -> str:
        text = " ".join([
            str(record.get("original_query", "")),
            str((record.get("siis_response") or {}).get("title", "")),
        ]).lower()
        for domain, terms in DOMAIN_TERMS.items():
            if any(t in text for t in terms):
                return domain
        return "display"

    def _variants(self, record: dict) -> list[str]:
        si = record.get("siis_response") or {}
        title = str(si.get("title", ""))
        original = str(record.get("original_query", ""))
        content = str(si.get("content", ""))
        # Keep the index compact: query + title are the highest-signal text.
        return [x for x in (original, title) if x.strip()] or [content[:1000]]

    def _symptoms(self, record: dict) -> list[str]:
        text = " ".join(self._variants(record)).lower()
        mapping = (
            ("fast_battery_drain", ("battery", "charge", "drain")),
            ("overheating", ("hot", "overheat")),
            ("blank_screen", ("blank", "black screen")),
            ("screen_damage", ("cracked", "bleeding", "damage")),
            ("touchscreen_issue", ("touchscreen", "touch")),
            ("screen_rotation_issue", ("rotate", "rotation")),
            ("screen_flicker", ("flicker",)),
            ("camera_issue", ("camera",)),
            ("data_transfer_issue", ("data transfer", "transfer data")),
            ("email_issue", ("email",)),
        )
        return [name for name, terms in mapping if any(t in text for t in terms)]

    def _load_and_build(self):
        with open(self.dataset_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        self._scenarios = payload["responses"]

        vectors = []
        for scenario in self._scenarios:
            variants = self._variants(scenario)
            vecs = embeddings.embed_batch(variants)
            centroid = vecs.mean(axis=0)
            norm = np.linalg.norm(centroid)
            if norm:
                centroid = centroid / norm
            vectors.append(centroid)

        if vectors:
            matrix = np.vstack(vectors).astype(np.float32)
            import faiss
            self._index = faiss.IndexFlatIP(matrix.shape[1])
            self._index.add(matrix)

    def search(self, normalized_query: str, top_k: int = DEFAULT_TOP_K) -> List[Candidate]:
        if not normalized_query:
            return []
        return self.search_vec(embeddings.embed_text(normalized_query), top_k)

    def search_vec(self, query_vec: np.ndarray, top_k: int = DEFAULT_TOP_K) -> List[Candidate]:
        if self._index is None or not self._scenarios:
            return []
        query_vec = query_vec.reshape(1, -1)
        top_k = min(top_k, len(self._scenarios))
        similarities, indices = self._index.search(query_vec, top_k)
        results = []
        for sim, idx in zip(similarities[0], indices[0]):
            if idx < 0:
                continue
            scenario = self._scenarios[idx]
            results.append(Candidate(
                scenario_id=scenario["id"],
                domain=self._domain(scenario),
                description=str((scenario.get("siis_response") or {}).get("title", "")),
                similarity=float(sim),
            ))
        return results

    def get_scenario(self, scenario_id: str) -> dict | None:
        return next((s for s in self._scenarios if s["id"] == scenario_id), None)
