"""
embeddings.py
Owner: Language Brain (Kavyansh)

Responsible ONLY for text -> vector conversion. Hides the embedding
model/provider details from the rest of the system (retrieval.py,
semantic_cache.py just call embed_text()/embed_batch()).

Uses a local sentence-transformers model - no API calls, no cost,
works offline. Good for hackathon demo reliability.
"""

import os
from functools import lru_cache
from typing import List

import numpy as np

# Model name is configurable via env var - never hardcode in multiple places.
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

_model = None  # lazy-loaded singleton


def _get_model():
    """Lazy-load the sentence-transformers model once (expensive to load)."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


def embed_text(text: str) -> np.ndarray:
    """
    Convert a single string into an embedding vector.
    Returns a normalized numpy array (unit length) so cosine similarity
    can be computed via simple dot product downstream.
    """
    if not text or not text.strip():
        # Return a zero vector for empty input rather than crashing -
        # callers should treat this as "no meaningful signal".
        model = _get_model()
        dim = model.get_sentence_embedding_dimension()
        return np.zeros(dim, dtype=np.float32)

    model = _get_model()
    vec = model.encode(text, normalize_embeddings=True, convert_to_numpy=True)
    return vec.astype(np.float32)


def embed_batch(texts: List[str]) -> np.ndarray:
    """
    Convert a list of strings into a 2D array of embeddings (N x dim).
    Used when building the scenario index (retrieval.py) so we don't
    encode scenario descriptions one at a time.
    """
    if not texts:
        return np.array([])

    model = _get_model()
    vecs = model.encode(
        texts, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False
    )
    return vecs.astype(np.float32)


def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """
    Cosine similarity between two vectors. Since embeddings are already
    normalized (unit length), this is just the dot product.
    """
    if vec_a.size == 0 or vec_b.size == 0:
        return 0.0
    return float(np.dot(vec_a, vec_b))


def get_embedding_dimension() -> int:
    """Expose the vector dimension for retrieval.py to size its FAISS index."""
    m = _get_model()
    fn = getattr(m, "get_embedding_dimension", None) or m.get_sentence_embedding_dimension
    return fn()


if __name__ == "__main__":
    # Quick manual sanity check: paraphrases should have high similarity
    a = embed_text("My battery dies really fast")
    b = embed_text("Phone loses charge insanely quickly")
    c = embed_text("My camera won't focus")

    print("battery vs battery (paraphrase):", cosine_similarity(a, b))
    print("battery vs camera (unrelated):  ", cosine_similarity(a, c))
    print("embedding dimension:", get_embedding_dimension())
