from __future__ import annotations
import re
from .models import Goal, Action, StepGroup, actionCategory

HEADING_RE=re.compile(r"^\s*#{1,3}\s*(.+?)\s*$",re.M)
MANUAL_WORDS=("contact customer support","contact your","service center","service centre","repair service","authorized service","walk-in service","mail-in repair","further assistance")
CRITICAL_WORDS=("factory data reset","factory reset","reset your device","reset all","firmware update")

def clean(s:str)->str:
    s=re.sub(r"https?://\S+|www\.\S+", "", s, flags=re.I)
    s=re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)
    s=re.sub(r"^\s*(?:[-*•]+|\d+[.)])\s*", "", s)
    return " ".join(s.split()).strip()

def split_sentences(text:str)->list[str]:
    text=clean(text)
    if not text:return []
    parts=re.split(r"(?<=[.!?])\s+",text)
    return [p.strip() for p in parts if len(p.strip())>=8]

def blocks(content:str):
    matches=list(HEADING_RE.finditer(content))
    if not matches:
        return [("Troubleshooting steps", content)]
    out=[]
    for i,m in enumerate(matches):
        start=m.end()
        end=matches[i+1].start() if i+1<len(matches) else len(content)
        body=content[start:end].strip()
        if body:
            out.append((clean(m.group(1)),body))
    return out

def category(name:str,body:str):
    t=(name+" "+body).lower()
    if any(x in t for x in CRITICAL_WORDS): return actionCategory.critical
    if any(x in t for x in MANUAL_WORDS): return actionCategory.manual
    return actionCategory.auto

def description(name:str)->str:
    n=name.lower()
    if "restart" in n or "reboot" in n: return "It will restart the device safely."
    if "update" in n: return "It will update software for stability."
    if "reset" in n: return "It will reset the device to defaults."
    if "contact" in n or "service" in n or "repair" in n or "assistance" in n: return "It will guide you toward service."
    if "cache" in n or "storage" in n: return "It will clear temporary app data safely."
    return "It will guide this troubleshooting step safely."

def short_title(raw:str)->str:
    s=raw.lower()
    if "blank" in s or "black display" in s: return "Blank Display"
    if "cracked" in s or "bleeding" in s: return "Screen Damage"
    if "touchscreen" in s: return "Touchscreen Issues"
    if "rotate" in s: return "Screen Rotation"
    if "multi window" in s: return "Multi Window"
    if "screen mirroring" in s: return "Screen Mirroring"
    if "email" in s: return "Email Issues"
    if "camera" in s and "flicker" in s: return "Camera Flicker"
    if "data" in s and "screen" in s: return "Data Access"
    words=[w for w in re.findall(r"[a-z0-9]+",s) if w not in {"on","for","a","an","the","your","smartphone","tablet","device","or","and","to","use","with"}]
    return " ".join(words[:2]).title() if words else "Device Issue"

def extract(record:dict, score:float)->Goal:
    si=record.get("siis_response") or {}
    title_raw=str(si.get("title") or "Device troubleshooting")
    content=str(si.get("content") or "")
    actions=[]
    for name,body in blocks(content):
        steps=split_sentences(body)
        if not steps: continue
        actions.append(Action(actionName=name,description=description(name),category=category(name,body),stepGroups=[StepGroup(steps=steps)]))
    if not actions:
        raise ValueError("No actionable source text found")
    rank={actionCategory.auto:0,actionCategory.manual:1,actionCategory.critical:2}
    actions.sort(key=lambda a:rank[a.category])
    topic=short_title(title_raw)
    goal=f"Follow these steps to perform this {topic} Troubleshooting"
    return Goal(goal=goal,title=topic,score=max(0,min(1,float(score))),actions=actions)
