from __future__ import annotations
import re
from difflib import SequenceMatcher
from .catalog import DeviceCatalog

STOP={"open","tap","select","choose","the","a","an","settings","screen","page","menu","go","to","navigate","your","my"}

def tokens(s: str)->set[str]:
    return {x for x in re.findall(r"[a-z0-9]+",s.lower()) if len(x)>2 and x not in STOP}

def score(q: str,c: str)->float:
    a,b=tokens(q),tokens(c)
    if not a or not b:return 0
    overlap=len(a&b)/len(a)
    fuzzy=SequenceMatcher(None,q.lower(),c.lower()).ratio()
    return .7*overlap+.3*fuzzy

class DeeplinkMapper:
    def __init__(self,catalog:DeviceCatalog): self.catalog=catalog

    def map(self, action_name:str, steps:list[str])->str|None:
        best=None
        for record in self.catalog.deeplink_records():
            uri=next((record.get(k) for k in ("actionableDeeplink","deeplink","masked_uri","maskedUri","uri","url")
                      if isinstance(record.get(k),str) and record.get(k).strip()),None)
            if not uri or re.match(r"^https?://",uri,re.I): continue
            text=" ".join(str(record.get(k,"")) for k in
                          ("name","title","description","message","qna_description","qnaDescription","action","screen","category"))
            for q in (action_name,*steps):
                s=score(q,text)
                if best is None or s>best[0]: best=(s,uri)
        return best[1] if best and best[0]>=.45 else None
