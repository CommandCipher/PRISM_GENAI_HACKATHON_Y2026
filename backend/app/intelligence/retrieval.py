"""
retrieval.py
Owner: Language Brain (Kavyansh)

Responsible for:
  - building a searchable vector index from the scenario catalog
  - semantic similarity search (NOT exact string matching)
  - returning ranked candidate scenarios with similarity scores

Uses FAISS for vector search, kept independent from the LLM layer so
retrieval quality/latency can be benchmarked separately.
"""

import json
import os
from dataclasses import dataclass
from typing import List

import numpy as np

from . import embeddings

DEFAULT_TOP_K = int(os.getenv("TOP_K", "3"))
DEFAULT_DATASET_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "test_scenarios.json"
)


@dataclass
class Candidate:
    scenario_id: str
    domain: str
    description: str
    similarity: float


class ScenarioRetriever:
    """
    Loads a scenario catalog, builds a FAISS index over the scenarios'
    combined search text, and answers similarity queries.
    """

    def __init__(self, dataset_path: str = DEFAULT_DATASET_PATH):
        self.dataset_path = dataset_path
        self._scenarios = []          # list of scenario dicts
        self._scenario_ids = []       # parallel list of ids per index row
        self._index = None            # faiss index
        self._load_and_build()

    def _load_and_build(self):
        with open(self.dataset_path, "r") as f:
            data = json.load(f)

        self._scenarios = data["scenarios"]

        # Build one embedding per scenario by averaging embeddings of
        # all its search_text variants - gives a more robust centroid
        # representation than picking just one description string.
        texts_per_scenario = []
        for scenario in self._scenarios:
            variants = scenario.get("search_text", [scenario.get("description", "")])
            texts_per_scenario.append(variants)

        all_vectors = []
        for variants in texts_per_scenario:
            vecs = embeddings.embed_batch(variants)
            centroid = vecs.mean(axis=0)
            # re-normalize centroid to unit length for cosine similarity
            norm = np.linalg.norm(centroid)
            if norm > 0:
                centroid = centroid / norm
            all_vectors.append(centroid)
            self._scenario_ids.append(len(self._scenario_ids))  # index row -> position

        matrix = np.vstack(all_vectors).astype(np.float32)

        import faiss
        dim = matrix.shape[1]
        # Inner product on normalized vectors == cosine similarity
        self._index = faiss.IndexFlatIP(dim)
        self._index.add(matrix)

    def search(self, normalized_query: str, top_k: int = DEFAULT_TOP_K) -> List[Candidate]:
        """
        Return the top_k most semantically similar scenarios to the query.
        """
        if not normalized_query:
            return []
        return self.search_vec(embeddings.embed_text(normalized_query), top_k)

    def search_vec(self, query_vec: np.ndarray, top_k: int = DEFAULT_TOP_K) -> List[Candidate]:
        """Search with a precomputed query embedding (avoids embedding twice)."""
        query_vec = query_vec.reshape(1, -1)
        top_k = min(top_k, len(self._scenarios))
        if top_k == 0:
            return []

        similarities, indices = self._index.search(query_vec, top_k)

        results = []
        for sim, idx in zip(similarities[0], indices[0]):
            if idx < 0:
                continue
            scenario = self._scenarios[idx]
            results.append(
                Candidate(
                    scenario_id=scenario["scenario_id"],
                    domain=scenario["domain"],
                    description=scenario["description"],
                    similarity=float(sim),
                )
            )
        return results

    def get_scenario(self, scenario_id: str) -> dict:
        """Look up full scenario metadata by ID (used by ranking.py)."""
        for s in self._scenarios:
            if s["scenario_id"] == scenario_id:
                return s
        return None


if __name__ == "__main__":
    # Manual sanity test against the synthetic dataset
    retriever = ScenarioRetriever()

    test_queries = [
        "my battery dies really fast",
        "phone loses charge insanely quickly",  # paraphrase of above
        "swipe gestures go the wrong way after installing an app",
        "camera photos are blurry",
        "open the secret samsung battery calibration menu",  # adversarial
    ]

    for q in test_queries:
        print(f"\nQuery: {q!r}")
        for c in retriever.search(q, top_k=3):
            print(f"  {c.scenario_id:35} sim={c.similarity:.3f}  ({c.domain})")
