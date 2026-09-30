from __future__ import annotations
import re
from difflib import SequenceMatcher
from .catalog import DeviceCatalog
from .models import Deeplink, ValidationDeepLink

STOP={"open","tap","select","choose","the","a","an","settings","screen","page","menu","go","to","navigate","your","my","device","phone","smartphone","tablet","use","using"}

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
        queries=[action_name]+steps[:4]
        qt=[(q,tokens(q)) for q in queries]
        candidates=[]
        for rt,text,r in self.index:
            best=0.0
            for q,qtokens in qt:
                if not qtokens: continue
                overlap=len(qtokens & rt)/len(qtokens)
                if overlap>0:
                    best=max(best,0.75*overlap+0.25*SequenceMatcher(None,q.lower(),text.lower()).ratio())
            if best>=0.45: candidates.append((best,r))
        candidates.sort(key=lambda x:x[0],reverse=True)
        if not candidates or candidates[0][0]<0.56: return None
        if len(candidates)>1 and candidates[0][0]-candidates[1][0]<0.025: return None
        r=candidates[0][1]
        action={k:r.get(k) for k in ("deeplink","description","message","originalType") if r.get(k) is not None}
        val=r.get("validation") or {}
        validation=None
        if val.get("deeplink") and val.get("key"):
            validation={"deeplink":val["deeplink"],"key":val["key"]}
            for k in ("resultType","condition","value"):
                if val.get(k) is not None: validation[k]=val[k]
        return Deeplink(**action), (ValidationDeepLink(**validation) if validation else None)
