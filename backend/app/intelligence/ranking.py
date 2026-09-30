"""
ranking.py
Owner: Language Brain (Kavyansh)

Takes raw retrieval similarity scores and refines them into a more
trustworthy confidence score. Retrieval similarity alone is NOT the
same as semantic correctness (per handoff doc section 43).

Keep this explainable - we should be able to say why a candidate
was ranked where it was.
"""

from dataclasses import dataclass
from typing import List, Optional

from .retrieval import Candidate

# Weights are intentionally simple and explainable (not learned) -
# appropriate for a hackathon timeline. Tune experimentally.
WEIGHT_SIMILARITY = 0.7
WEIGHT_DOMAIN_MATCH = 0.2
WEIGHT_SYMPTOM_OVERLAP = 0.1

# Below this, we don't trust the top candidate at all.
LOW_CONFIDENCE_THRESHOLD = 0.45


@dataclass
class RankedCandidate:
    scenario_id: str
    domain: str
    retrieval_similarity: float
    confidence: float  # calibrated, not just raw similarity


def rank_candidates(
    candidates: List[Candidate],
    inferred_domain: Optional[str] = None,
    inferred_symptoms: Optional[List[str]] = None,
    scenario_lookup=None,  # callable: scenario_id -> scenario dict (for symptom overlap)
) -> List[RankedCandidate]:
    """
    Re-score raw retrieval candidates using domain/symptom consistency
    signals, producing a calibrated confidence distinct from raw
    cosine similarity.
    """
    inferred_symptoms = set(inferred_symptoms or [])
    ranked = []

    for c in candidates:
        score = WEIGHT_SIMILARITY * c.similarity

        # Domain consistency bonus
        if inferred_domain and c.domain == inferred_domain:
            score += WEIGHT_DOMAIN_MATCH
        elif inferred_domain and c.domain != inferred_domain:
            # Mismatch penalty - don't let a high-similarity but
            # wrong-domain result dominate.
            score -= WEIGHT_DOMAIN_MATCH * 0.5

        # Symptom overlap bonus
        if scenario_lookup and inferred_symptoms:
            scenario = scenario_lookup(c.scenario_id)
            scenario_symptoms = set(scenario.get("symptoms", [])) if scenario else set()
            overlap = len(inferred_symptoms & scenario_symptoms)
            if overlap > 0:
                score += WEIGHT_SYMPTOM_OVERLAP * min(overlap, 2) / 2

        # Clamp to [0, 1]
        confidence = max(0.0, min(1.0, score))

        ranked.append(
            RankedCandidate(
                scenario_id=c.scenario_id,
                domain=c.domain,
                retrieval_similarity=c.similarity,
                confidence=confidence,
            )
        )

    ranked.sort(key=lambda r: r.confidence, reverse=True)
    return ranked


def is_ambiguous(ranked: List[RankedCandidate]) -> bool:
    """
    Decide whether the top candidate is trustworthy enough to commit to,
    or whether this should be treated as ambiguous (per handoff section 44:
    don't force a classification like BATTERY_FAST_DRAIN on "my phone is bad").
    """
    if not ranked:
        return True
    top = ranked[0]
    if top.confidence < LOW_CONFIDENCE_THRESHOLD:
        return True
    # If top-2 candidates are very close, it's ambiguous which one is right.
    if len(ranked) > 1 and (top.confidence - ranked[1].confidence) < 0.08:
        return True
    return False


if __name__ == "__main__":
    from .retrieval import Candidate

    fake_candidates = [
        Candidate("BATTERY_FAST_DRAIN", "battery", "desc", 0.91),
        Candidate("BATTERY_HEATING", "battery", "desc", 0.85),
        Candidate("CAMERA_FOCUS_ISSUE", "camera", "desc", 0.40),
    ]

    ranked = rank_candidates(
        fake_candidates,
        inferred_domain="battery",
        inferred_symptoms=["fast_battery_drain"],
    )
    for r in ranked:
        print(r)
    print("Ambiguous?", is_ambiguous(ranked))
