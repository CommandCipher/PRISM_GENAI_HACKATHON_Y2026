from __future__ import annotations
import copy
from app.intelligence.language_brain import analyze
from app.device_brain.catalog import DeviceCatalog
from app.device_brain.extractor import extract
from app.device_brain.deeplink import DeeplinkMapper
from app.device_brain.guard import ValidationGuard
from app.device_brain.models import ContextDeeplinkResponse

catalog=DeviceCatalog()
mapper=DeeplinkMapper(catalog)
guard=ValidationGuard(catalog)

# Deterministic Device Brain output cache. Once a scenario has passed extraction,
# catalog-only deeplink mapping, and the validation guard, the same validated
# response can be reused without rescanning the 578-entry deeplink catalog.
_VALIDATED_GOAL_CACHE: dict[str, dict] = {}

def _choose(query:str, intelligence:dict):
    candidates=intelligence.get("candidates",[]) if isinstance(intelligence,dict) else []
    for c in candidates:
        sid=c.get("scenario_id")
        if sid and catalog.scenario(sid):
            return catalog.scenario(sid),float(c.get("confidence",0.0))
    hit=catalog.match_query(query)
    if hit and hit[0]>=0.45:
        return hit[1],hit[0]
    return None,0.0

def troubleshoot(query:str)->dict:
    intelligence={}
    try:
        intelligence=analyze(query) or {}
    except Exception:
        intelligence={}

    record,score=_choose(query,intelligence)
    if not record:
        return {"query":query,"response":{"contexts":[]}}

    scenario_id=str(record.get("id") or "")
    cached_goal=_VALIDATED_GOAL_CACHE.get(scenario_id)
    if cached_goal is not None:
        validated=ContextDeeplinkResponse(**copy.deepcopy(cached_goal))
        metadata=intelligence.get("metadata",{}) if isinstance(intelligence,dict) else {}
        return {
            "query":query,
            "response":validated.model_dump(mode="json"),
            "metadata":{
                "scenario_id": scenario_id,
                "cache_hit": bool(metadata.get("cache_hit",False)),
                "device_brain_cache_hit": True,
                "latency_ms": metadata.get("total_latency_ms"),
            }
        }

    try:
        goal=extract(record,score)
    except Exception:
        return {"query":query,"response":{"contexts":[]}}

    for action in goal.actions:
        for group in action.stepGroups:
            if action.category.value=="manual":
                continue
            mapped=mapper.map(action.actionName,group.steps)
            if mapped:
                group.actionableDeeplink=mapped[0]
                group.validationDeeplink=mapped[1]

    errors=guard.validate(goal)
    if errors:
        return {"query":query,"response":{"contexts":[]}}

    validated=ContextDeeplinkResponse(contexts=[goal])
    payload=validated.model_dump(mode="json")
    if scenario_id:
        _VALIDATED_GOAL_CACHE[scenario_id]=copy.deepcopy(payload)

    metadata=intelligence.get("metadata",{}) if isinstance(intelligence,dict) else {}
    return {
        "query":query,
        "response":payload,
        "metadata":{
            "scenario_id": scenario_id,
            "cache_hit": bool(metadata.get("cache_hit",False)),
            "device_brain_cache_hit": False,
            "latency_ms": metadata.get("total_latency_ms"),
        }
    }
