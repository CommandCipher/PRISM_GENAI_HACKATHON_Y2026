"""
Diagnostic script: prints ACTUAL cosine similarity between paraphrase
pairs and unrelated pairs, after normalization, so we can pick a real
SEMANTIC_CACHE_THRESHOLD instead of guessing.

Run from backend/:  python scripts/tune_cache_threshold.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.intelligence import normalization, embeddings

# Pairs that SHOULD hit the cache together (same underlying problem)
SHOULD_MATCH = [
    ("my battery dies really fast", "phone loses charge insanely quickly"),
    ("my battery dies really fast", "battery drains like crazy these days"),
    ("phone loses charge insanely quickly", "battery drains like crazy these days"),
]

# Pairs that should NOT hit the cache together (related domain, different problem)
SHOULD_NOT_MATCH = [
    ("my battery dies really fast", "phone gets super hot and battery drops"),
    ("battery drains like crazy these days", "phone gets super hot and battery drops"),
]

# Pairs from completely different domains - similarity floor
UNRELATED = [
    ("my battery dies really fast", "swipe gestures go the wrong way after installing an app"),
]


def sim_after_normalization(a, b):
    na, nb = normalization.normalize_query(a), normalization.normalize_query(b)
    va, vb = embeddings.embed_text(na), embeddings.embed_text(nb)
    return embeddings.cosine_similarity(va, vb)


def run(title, pairs):
    print(f"\n--- {title} ---")
    scores = []
    for a, b in pairs:
        s = sim_after_normalization(a, b)
        scores.append(s)
        print(f"{s:.3f}   {a!r}  <->  {b!r}")
    return scores


if __name__ == "__main__":
    should_match_scores = run("SHOULD hit cache together (paraphrases)", SHOULD_MATCH)
    should_not_scores = run("SHOULD NOT hit cache together (different problem, same domain)", SHOULD_NOT_MATCH)
    unrelated_scores = run("Unrelated domains (similarity floor)", UNRELATED)

    print("\n=== Summary ===")
    print(f"Lowest 'should match' score:      {min(should_match_scores):.3f}  <- threshold must be BELOW this")
    print(f"Highest 'should NOT match' score: {max(should_not_scores):.3f}  <- threshold must be ABOVE this")
    if min(should_match_scores) > max(should_not_scores):
        suggested = (min(should_match_scores) + max(should_not_scores)) / 2
        print(f"\nThere IS a safe gap. Suggested SEMANTIC_CACHE_THRESHOLD = {suggested:.2f}")
    else:
        print("\nWARNING: no clean gap between 'should match' and 'should not match' scores.")
        print("Similarity alone can't safely separate these - the domain/symptom check")
        print("in the cache (or ranking) needs to carry more of the weight here.")
