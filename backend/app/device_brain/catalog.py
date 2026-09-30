from __future__ import annotations
import json, os, re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("DEVICE_DATA_DIR", str(ROOT / "data")))

def _load(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def _records(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in ("scenarios", "items", "records", "data", "responses"):
            if isinstance(payload.get(key), list):
                return [x for x in payload[key] if isinstance(x, dict)]
        return [dict(v, scenario_id=k) if isinstance(v, dict) else {"scenario_id": k, "text": v}
                for k, v in payload.items() if isinstance(v, (dict, str))]
    return []

def _first(d: dict, keys: tuple[str, ...]) -> str | None:
    for k in keys:
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None

class DeviceCatalog:
    """
    Loads the real starter assets when they are placed in backend/app/data:
      siis_responses.json / queries.json / deeplinks.json
    The loader accepts common wrapper/field variants so integration does not
    depend on one guessed JSON layout.
    """
    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir
        self.scenarios: dict[str, dict] = {}
        self.deeplinks: list[dict] = []
        self.reload()

    def reload(self):
        payload = _load(self.data_dir / "siis_responses.json")
        if payload is None:
            payload = _load(self.data_dir / "queries.json")
        for r in _records(payload):
            sid = _first(r, ("scenario_id","scenarioId","id","query_id","queryId"))
            if sid:
                self.scenarios[str(sid)] = r

        dl = _load(self.data_dir / "deeplinks.json")
        self.deeplinks = _records(dl)

    def scenario(self, scenario_id: str) -> dict | None:
        return self.scenarios.get(str(scenario_id))

    def exact_deeplink_values(self) -> set[str]:
        values = set()
        for r in self.deeplinks:
            v = _first(r, ("actionableDeeplink","deeplink","masked_uri","maskedUri","uri","url"))
            if v and not re.match(r"^https?://", v, re.I):
                values.add(v)
        return values

    def deeplink_records(self) -> list[dict]:
        return self.deeplinks
