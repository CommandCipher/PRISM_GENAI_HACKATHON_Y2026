from __future__ import annotations
import re
from difflib import SequenceMatcher
from .catalog import DeviceCatalog
from .models import Deeplink, ValidationDeepLink

STOP={"open","tap","select","choose","the","a","an","settings","screen","page","menu","go","to","navigate","your","my","device","phone","smartphone","tablet","use","using","step","check","review","verify","attempt"}

def tokens(s:str)->set[str]:
    return {x for x in re.findall(r"[a-z0-9]+",s.lower()) if len(x)>2 and x not in STOP}

def _field_score(query:str, record:dict)->float:
    qt=tokens(query)
    if not qt: return 0.0
    best=0.0
    for field,weight in (("message",0.55),("description",0.30),("qna_description",0.15)):
        text=str(record.get(field) or "")
        rt=tokens(text)
        overlap=len(qt & rt)/len(qt)
        fuzzy=SequenceMatcher(None,query.lower(),text.lower()).ratio()
        best=max(best,weight*(0.70*overlap+0.30*fuzzy))
    return best

def _direction_bonus(query:str, record:dict)->float:
    q=query.lower()
    typ=str(record.get("originalType") or "").lower()
    positive=any(x in q for x in ("enable","turn on","switch on","allow","activate","select","use"))
    negative=any(x in q for x in ("disable","turn off","switch off","block","deactivate","remove"))
    if positive and "onurl" in typ: return 0.08
    if negative and "offurl" in typ: return 0.08
    if positive and "offurl" in typ: return -0.08
    if negative and "onurl" in typ: return -0.08
    return 0.0

class DeeplinkMapper:
    def __init__(self,catalog:DeviceCatalog):
        self.catalog=catalog
        self.index=[
            r for r in catalog.deeplink_records()
            if isinstance(r.get("deeplink"),str)
            and r["deeplink"].startswith("voiceassist://")
            and r["deeplink"] != "voiceassist://dummy_positive"
        ]

    def map(self, action_name:str, steps:list[str]):
        queries=[action_name]+steps
        ranked=[]
        for r in self.index:
            action_score=_field_score(action_name,r)
            step_score=max((_field_score(s,r) for s in steps), default=0.0)
            score=0.80*action_score+0.20*step_score+_direction_bonus(" ".join(queries),r)
            if score>=0.30:
                ranked.append((score,r))
        ranked.sort(key=lambda x:x[0],reverse=True)
        if not ranked or ranked[0][0] < 0.34:
            return None
        if len(ranked)>1 and ranked[0][0]-ranked[1][0] < 0.015:
            return None
        r=ranked[0][1]
        action=Deeplink(
            deeplink=r["deeplink"],
            description=r["description"],
            message=r.get("message",""),
            classes=r.get("classes"),
            originalType=r.get("originalType"),
        )
        val=r.get("validation") or {}
        validation=None
        if val.get("deeplink") and val.get("key"):
            validation=ValidationDeepLink(
                deeplink=val["deeplink"],
                key=val["key"],
                resultType=val.get("resultType"),
                condition=val.get("condition"),
                value=val.get("value"),
            )
        return action,validation
