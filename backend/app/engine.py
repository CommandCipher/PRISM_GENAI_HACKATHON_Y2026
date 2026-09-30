from __future__ import annotations
from app.intelligence.language_brain import analyze
from app.device_brain.catalog import DeviceCatalog
from app.device_brain.extractor import extract
from app.device_brain.deeplink import DeeplinkMapper
from app.device_brain.guard import ValidationGuard
from app.device_brain.models import ContextDeeplinkResponse

catalog=DeviceCatalog()
mapper=DeeplinkMapper(catalog)
guard=ValidationGuard(catalog)

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
    catalog.reload()
    global mapper,guard
    mapper=DeeplinkMapper(catalog)
    guard=ValidationGuard(catalog)
    record,score=_choose(query,intelligence)
    if not record:
        return {"query":query,"response":{"contexts":[]}}
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
    return {
        "query":query,
        "response":validated.model_dump(mode="json"),
        "metadata":{
            "scenario_id": next((c.get("scenario_id") for c in intelligence.get("candidates",[]) if c.get("scenario_id")),None),
            "cache_hit": intelligence.get("metadata",{}).get("cache_hit",False),
            "latency_ms": intelligence.get("metadata",{}).get("total_latency_ms"),
        }
    }
