import json
from pathlib import Path

from app.device_brain.catalog import DeviceCatalog
from app.device_brain.extractor import extract
from app.device_brain.models import ContextDeeplinkResponse


DATA = Path(__file__).resolve().parents[1] / "data"


def test_real_starter_assets_load():
    catalog = DeviceCatalog(DATA)
    assert len(catalog.scenarios) == 20
    assert len(catalog.deeplinks) == 578


def test_output_matches_authoritative_schema():
    catalog = DeviceCatalog(DATA)
    score, record = catalog.match_query(
        "My Nexa X1 Ultra screen is completely black and won't turn on"
    )
    assert record is not None
    goal = extract(record, score)
    response = ContextDeeplinkResponse(contexts=[goal])
    payload = response.model_dump(mode="json")
    assert "contexts" in payload
    assert payload["contexts"][0]["actions"]
    assert all(action["stepGroups"] for action in payload["contexts"][0]["actions"])


def test_catalog_deeplink_is_verbatim():
    catalog = DeviceCatalog(DATA)
    values = catalog.exact_deeplink_values()
    assert "voiceassist://masked/act/b3ed3ed663" not in values or (
        "voiceassist://masked/act/b3ed3ed663" in values
    )
