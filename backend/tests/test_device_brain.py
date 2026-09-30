from pathlib import Path
from app.device_brain.catalog import DeviceCatalog
from app.device_brain.extractor import extract
from app.device_brain.models import ContextDeeplinkResponse

DATA = Path(__file__).resolve().parents[1] / "data"

def test_real_starter_assets_load():
    catalog = DeviceCatalog(DATA)
    assert len(catalog.scenarios) == 20
    assert len(catalog.deeplinks) == 578

def test_schema_can_validate_source_record():
    catalog = DeviceCatalog(DATA)
    score, record = catalog.match_query("My Nexa X1 screen is completely blank")
    assert record is not None
    goal = extract(record, score)
    payload = ContextDeeplinkResponse(contexts=[goal]).model_dump(mode="json")
    assert payload["contexts"][0]["actions"]
    assert all(a["stepGroups"] for a in payload["contexts"][0]["actions"])

def test_deeplink_catalog_is_exact():
    catalog = DeviceCatalog(DATA)
    values = catalog.exact_deeplink_values()
    assert len(values) == 578
    assert all(v.startswith("voiceassist://") for v in values)
