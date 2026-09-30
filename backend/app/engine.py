from __future__ import annotations
from app.intelligence.language_brain import analyze
from app.device_brain.catalog import DeviceCatalog
from app.device_brain.extractor import extract
from app.device_brain.deeplink import DeeplinkMapper
from app.device_brain.guard import ValidationGuard

catalog=DeviceCatalog()
mapper=DeeplinkMapper(catalog)
guard=ValidationGuard(catalog)

def troubleshoot(query:str)->dict:
    intelligence=analyze(query)
    candidates=intelligence.get("candidates",[])
    if not candidates:
        return {"status":"error","code":"NO_MATCH","message":"No validated troubleshooting scenario matched.","intelligence":intelligence}
    chosen=candidates[0]
    scenario=catalog.scenario(chosen["scenario_id"])
    if not scenario:
        return {"status":"error","code":"SCENARIO_NOT_FOUND","message":"Candidate scenario has no reference record.","scenario_id":chosen["scenario_id"]}
    reference=next((scenario.get(k) for k in ("siis_response","reference","reference_text","response","text","content","instructions") if isinstance(scenario.get(k),str) and scenario.get(k).strip()),None)
    if not reference:
        return {"status":"error","code":"NO_REFERENCE_TEXT","message":"Scenario has no reference troubleshooting text.","scenario_id":chosen["scenario_id"]}
    goal=extract(reference,intelligence.get("complaint_dna",{}).get("canonical_query",query),chosen.get("confidence",0))
    for action in goal.actions:
        if action.category!="manual":
            steps=[s for g in action.stepGroups for s in g.steps]
            action.actionableDeeplink=mapper.map(action.actionName,steps)
    errors=guard.validate(goal)
    if errors:
        return {"status":"error","code":"VALIDATION_FAILED","message":"; ".join(errors),"scenario_id":chosen["scenario_id"]}
    return {"status":"ok","data":goal.model_dump(),"metadata":{"cache_hit":intelligence.get("metadata",{}).get("cache_hit",False),"scenario_id":chosen["scenario_id"],"confidence":chosen.get("confidence",0),"intelligence":intelligence.get("metadata",{})}}
