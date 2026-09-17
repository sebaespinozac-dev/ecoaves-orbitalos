from __future__ import annotations

from core.models import SOURCE_COPERNICUS_SENTINEL, SOURCE_CUBESAT_UA, SOURCE_NASA_EARTHDATA
from apps.darksky import DarkskyApp
from datahub.adapter import DiscoverCriteria
from simulators.memory import cubesat_adapter, nasa_adapter, sentinel_adapter


def _scenes(*adapters):
    scenes = []
    for adapter in adapters:
        for ref in adapter.discover(DiscoverCriteria()):
            if adapter.source == SOURCE_CUBESAT_UA and "schema-sample" in ref.granule_id:
                continue
            scenes.append(adapter.normalize(adapter.fetch(ref)))
    return scenes


def test_darksky_uses_nasa_and_optional_cubesat_with_provenance() -> None:
    report = DarkskyApp().process(
        _scenes(nasa_adapter(), cubesat_adapter()),
        batch_id="D1",
    )
    payload = report.payload
    assert payload["primary_source"] == SOURCE_NASA_EARTHDATA
    assert payload["sentinel_used"] is False
    assert payload["nasa_earthdata"]["present"] is True
    assert payload["cubesat_ua"]["present"] is True
    cited = payload["cubesat_ua"]["captures"][0]["level"]["provenance"]
    assert cited["source"] == SOURCE_CUBESAT_UA
    nasa_cite = payload["nasa_earthdata"]["granules"][0]["product_id"]["provenance"]
    assert nasa_cite["source"] == SOURCE_NASA_EARTHDATA
    assert "NASA" in report.summary_text
    cells = payload["cubesat_ua"]["captures"][0]["cells"]
    assert cells
    assert cells[0]["provenance"]["source"] == SOURCE_CUBESAT_UA


def test_darksky_ignores_sentinel_even_if_passed() -> None:
    report = DarkskyApp().process(_scenes(sentinel_adapter()), batch_id="D2")
    assert report.payload["sentinel_used"] is False
    assert report.payload["sentinel_scenes_ignored"] >= 1
    assert report.payload["nasa_earthdata"]["present"] is False
    assert SOURCE_COPERNICUS_SENTINEL not in report.payload["sources_used"]
