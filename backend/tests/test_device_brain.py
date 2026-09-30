from pathlib import Path

from app.device_brain.catalog import DeviceCatalog
from app.device_brain.deeplink import DeeplinkMapper
from app.device_brain.extractor import extract
from app.device_brain.models import ContextDeeplinkResponse

# Real hackathon assets live under backend/app/data.
DATA = Path(__file__).resolve().parents[1] / "app" / "data"

def test_real_starter_assets_load():
    catalog = DeviceCatalog(DATA)
    assert len(catalog.scenarios) == 20
    assert len(catalog.deeplinks) == 578

def test_schema_can_validate_real_source_record():
    catalog = DeviceCatalog(DATA)
    score, record = catalog.match_query("My Nexa X1 screen is completely blank")
    assert record is not None
    goal = extract(record, score)
    payload = ContextDeeplinkResponse(contexts=[goal]).model_dump(mode="json")
    assert payload["contexts"][0]["actions"]
    assert all(action["stepGroups"] for action in payload["contexts"][0]["actions"])

def test_deeplink_mapping_copies_exact_catalog_uri():
    catalog = DeviceCatalog(DATA)
    mapped = DeeplinkMapper(catalog).map(
        "Switch Time Format",
        ["Open the time format settings."],
    )
    assert mapped is not None
    action, validation = mapped
    assert action.deeplink == "voiceassist://masked/act/aa73a35e8d"
    assert validation is not None
    assert validation.deeplink == "voiceassist://masked/val/ef6814259a"

def test_deeplink_catalog_is_exact_and_non_generic():
    catalog = DeviceCatalog(DATA)
    values = catalog.exact_deeplink_values()
    assert len(values) == 578
    assert all(v.startswith("voiceassist://") for v in values)
    assert "voiceassist://dummy_positive" not in values
