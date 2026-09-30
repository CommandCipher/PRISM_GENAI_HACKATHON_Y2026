from pathlib import Path
from app.device_brain.catalog import DeviceCatalog
from app.device_brain.extractor import extract
from app.device_brain.models import ContextDeeplinkResponse
from app.device_brain.deeplink import DeeplinkMapper

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

def test_sample_backup_mapping_uses_exact_catalog_uri():
    catalog = DeviceCatalog(DATA)
    mapped = DeeplinkMapper(catalog).map(
        "Back Up Phone Data",
        [
            "Navigate to and open Settings.",
            "Tap on Accounts and backup.",
            "Select Back up data to secure your personal files.",
        ],
    )
    assert mapped is not None
    assert mapped[0].deeplink == "voiceassist://masked/act/b3ed3ed663"
    assert mapped[1] is not None
    assert mapped[1].deeplink == "voiceassist://masked/val/266037d0c5"

def test_deeplink_catalog_is_exact():
    catalog = DeviceCatalog(DATA)
    values = catalog.exact_deeplink_values()
    assert len(values) == 578
    assert all(v.startswith("voiceassist://") for v in values)
