from __future__ import annotations
import json, os, re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("DEVICE_DATA_DIR", str(ROOT / "data")))

def _load(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def _records(payload: Any, key: str | None = None) -> list[dict]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        if key and isinstance(payload.get(key), list):
            return [x for x in payload[key] if isinstance(x, dict)]
        for k in ("scenarios", "items", "records", "data", "responses", "deeplinks"):
            if isinstance(payload.get(k), list):
                return [x for x in payload[k] if isinstance(x, dict)]
    return []

def _norm(s: str) -> str:
    s = re.sub(r"[^a-z0-9 ]+", " ", s.lower())
    return " ".join(s.split())

def _tokens(s: str) -> set[str]:
    stop={"the","a","an","my","your","is","are","to","and","or","on","in","of","with","for","it","this","that","when","then","device","phone","smartphone","tablet"}
    return {x for x in _norm(s).split() if len(x)>2 and x not in stop}

class DeviceCatalog:
    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir=Path(data_dir)
        self.scenarios={}
        self.deeplinks=[]
        self.reload()

    def reload(self):
        payload=_load(self.data_dir/"siis_responses.json")
        self.scenarios={str(x.get("id")):x for x in _records(payload,"responses") if x.get("id")}
        dl=_load(self.data_dir/"deeplinks.json")
        self.deeplinks=_records(dl,"deeplinks")

    def scenario(self, scenario_id:str):
        return self.scenarios.get(str(scenario_id))

    def all_scenarios(self):
        return list(self.scenarios.values())

    def match_query(self, query:str):
        q=_norm(query); qt=_tokens(query); best=None
        for r in self.scenarios.values():
            si=r.get("siis_response") or {}
            original=str(r.get("original_query", ""))
            title=str(si.get("title", ""))
            overlap=len(qt & _tokens(original+" "+title))/max(1,len(qt))
            fuzzy=SequenceMatcher(None,q,_norm(original)).ratio()
            title_ratio=SequenceMatcher(None,q,_norm(title)).ratio()
            score=.55*overlap+.35*fuzzy+.10*title_ratio
            if best is None or score>best[0]:
                best=(score,r)
        return best

    def deeplink_records(self):
        return self.deeplinks

    def exact_deeplink_values(self):
        return {x.get("deeplink") for x in self.deeplinks if isinstance(x.get("deeplink"),str)}
