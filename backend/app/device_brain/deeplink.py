from __future__ import annotations
import re
from difflib import SequenceMatcher
from .catalog import DeviceCatalog
from .models import Deeplink, ValidationDeepLink

STOP={"open","tap","select","choose","the","a","an","settings","screen","page","menu","go","to","navigate","your","my","device","phone","smartphone","tablet","use","using","step","check","review","verify","attempt"}

def tokens(s:str)->set[str]:
    return {x for x in re.findall(r"[a-z0-9]+",s.lower()) if len(x)>2 and x not in STOP}

class DeeplinkMapper:
    def __init__(self,catalog:DeviceCatalog):
        self.catalog=catalog
        self.index=[]
        for r in catalog.deeplink_records():
            uri=r.get("deeplink")
            if not isinstance(uri,str) or not uri.strip() or re.match(r"^https?://",uri,re.I): continue
            text=" ".join(str(r.get(k) or "") for k in ("description","message","qna_description","originalType"))
            self.index.append((tokens(text),text,r))

    def map(self, action_name:str, steps:list[str]):
        queries=[action_name]+steps
        candidates=[]
        for rt,text,r in self.index:
            best=0.0
            for q in queries:
                qt=tokens(q)
                if not qt: continue
                overlap=len(qt & rt)/len(qt)
                if overlap:
                    fuzzy=SequenceMatcher(None,q.lower(),text.lower()).ratio()
                    best=max(best,0.80*overlap+0.20*fuzzy)
            if best>=0.50: candidates.append((best,r))
        candidates.sort(key=lambda x:x[0],reverse=True)
        if not candidates: return None
        # Require a meaningful margin to avoid choosing between near-duplicates.
        if candidates[0][0] < 0.58: return None
        if len(candidates)>1 and candidates[0][0]-candidates[1][0] < 0.02: return None
        r=candidates[0][1]
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
