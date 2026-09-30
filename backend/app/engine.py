from __future__ import annotations

import copy
import time

from app.intelligence import normalization
from app.intelligence.language_brain import analyze, fast_lookup
from app.device_brain.catalog import DeviceCatalog
from app.device_brain.extractor import extract
from app.device_brain.deeplink import DeeplinkMapper
from app.device_brain.guard import ValidationGuard
from app.device_brain.models import ContextDeeplinkResponse


catalog = DeviceCatalog()
mapper = DeeplinkMapper(catalog)
guard = ValidationGuard(catalog)

# Deterministic Device Brain output cache. Once a scenario has passed extraction,
# catalog-only deeplink mapping, and the validation guard, the same validated
# response can be reused without rescanning the 578-entry deeplink catalog.
_VALIDATED_GOAL_CACHE: dict[str, dict] = {}

# Exact normalized-query index for the true end-to-end fast path. The value is
# only populated after the complete response has passed the validation guard.
_VALIDATED_QUERY_CACHE: dict[str, tuple[str, dict]] = {}


def _choose(query: str, intelligence: dict):
    candidates = intelligence.get("candidates", []) if isinstance(intelligence, dict) else []
    for candidate in candidates:
        scenario_id = candidate.get("scenario_id")
        if scenario_id and catalog.scenario(scenario_id):
            return catalog.scenario(scenario_id), float(candidate.get("confidence", 0.0))

    hit = catalog.match_query(query)
    if hit and hit[0] >= 0.45:
        return hit[1], hit[0]

    return None, 0.0


def _response_metadata(
    intelligence: dict,
    scenario_id: str,
    device_cache_hit: bool,
    *,
    fast_path: bool = False,
    llm_call_avoided: bool = False,
    latency_ms: int | None = None,
) -> dict:
    metadata = intelligence.get("metadata", {}) if isinstance(intelligence, dict) else {}
    return {
        "scenario_id": scenario_id,
        "cache_hit": bool(metadata.get("cache_hit", False)),
        "device_brain_cache_hit": device_cache_hit,
        "fast_path": fast_path or bool(metadata.get("fast_path", False)),
        "llm_call_avoided": llm_call_avoided or bool(metadata.get("llm_call_avoided", False)),
        "latency_ms": latency_ms if latency_ms is not None else metadata.get("total_latency_ms"),
    }


def troubleshoot(query: str) -> dict:
    # First check the already-validated exact normalized query. This is the
    # fastest safe path and does not perform embeddings, retrieval, or LLM work.
    normalized_query = normalization.normalize_query(query)
    cached_query = _VALIDATED_QUERY_CACHE.get(normalized_query)
    if cached_query is not None:
        scenario_id, cached_goal = cached_query
        started = time.perf_counter()
        validated = ContextDeeplinkResponse(**copy.deepcopy(cached_goal))
        latency_ms = int((time.perf_counter() - started) * 1000)
        return {
            "query": query,
            "response": validated.model_dump(mode="json"),
            "metadata": _response_metadata(
                {},
                scenario_id,
                True,
                fast_path=True,
                llm_call_avoided=True,
                latency_ms=latency_ms,
            ),
        }

    # Otherwise use the Language Brain. Its semantic cache may still provide
    # a cheap LLM-free path for semantically similar queries.
    intelligence = {}
    try:
        intelligence = fast_lookup(query) or {}
        if not intelligence:
            intelligence = analyze(query) or {}
    except Exception:
        intelligence = {}

    record, score = _choose(query, intelligence)
    if not record:
        return {"query": query, "response": {"contexts": []}}

    scenario_id = str(record.get("id") or "")

    cached_goal = _VALIDATED_GOAL_CACHE.get(scenario_id)
    if cached_goal is not None:
        _VALIDATED_QUERY_CACHE[normalized_query] = (
            scenario_id,
            copy.deepcopy(cached_goal),
        )
        validated = ContextDeeplinkResponse(**copy.deepcopy(cached_goal))
        started = time.perf_counter()
        latency_ms = int((time.perf_counter() - started) * 1000)
        return {
            "query": query,
            "response": validated.model_dump(mode="json"),
            "metadata": _response_metadata(
                {},
                scenario_id,
                True,
                fast_path=True,
                llm_call_avoided=True,
                latency_ms=latency_ms,
            ),
        }

    try:
        goal = extract(record, score)
    except Exception:
        return {"query": query, "response": {"contexts": []}}

    for action in goal.actions:
        for group in action.stepGroups:
            if action.category.value == "manual":
                continue

            mapped = mapper.map(action.actionName, group.steps)
            if mapped:
                group.actionableDeeplink = mapped[0]
                group.validationDeeplink = mapped[1]

    errors = guard.validate(goal)
    if errors:
        return {"query": query, "response": {"contexts": []}}

    validated = ContextDeeplinkResponse(contexts=[goal])
    payload = validated.model_dump(mode="json")

    if scenario_id:
        _VALIDATED_GOAL_CACHE[scenario_id] = copy.deepcopy(payload)
        _VALIDATED_QUERY_CACHE[normalized_query] = (scenario_id, copy.deepcopy(payload))

    return {
        "query": query,
        "response": payload,
        "metadata": _response_metadata(intelligence, scenario_id, False),
    }
