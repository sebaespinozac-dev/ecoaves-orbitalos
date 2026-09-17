from __future__ import annotations

from core.models import NASA_BLACK_MARBLE_SUNSET, UA_ANALYSIS_CONTRACT
from simulators.copernicus_sentinel import S2_L2A_BANDS, sentinel_catalog
from simulators.cubesat_ua import SCHEMA_SAMPLE_ANALYSIS, cubesat_catalog
from simulators.nasa_earthdata import nasa_catalog


def test_cubesat_sample_matches_published_contract_illustration() -> None:
    assert SCHEMA_SAMPLE_ANALYSIS["contract"] == UA_ANALYSIS_CONTRACT
    assert SCHEMA_SAMPLE_ANALYSIS["level"] == "critico"
    cell = SCHEMA_SAMPLE_ANALYSIS["cells"][0]
    assert cell["flagged"] is True
    assert cell["blue_proxy"] == 0.6154


def test_cubesat_complete_fixture_fills_grid() -> None:
    complete = next(item for item in cubesat_catalog() if item["product_id"] == "CAP001")
    body = complete["body"]
    assert len(body["cells"]) == body["grid_cols"] * body["grid_rows"]
    assert complete["georeferenced"] is False


def test_nasa_fixtures_do_not_invent_cmr_concept_ids() -> None:
    for item in nasa_catalog():
        assert item["body"]["cmr_concept_id"] is None
        assert item["uri"].startswith("fixture://nasa_earthdata/")
        assert item["body"]["sds"] == "metadata_only"


def test_nasa_snpp_sunset_is_recorded() -> None:
    vnp = next(item for item in nasa_catalog() if item["product_id"] == "VNP46A1")
    assert vnp["body"]["snpp_delivery_ends"] == "2026-11-01"
    assert NASA_BLACK_MARBLE_SUNSET["VNP46A1"] == "2026-11-01"
    assert vnp["body"]["preferred_over_vnp46"] is False


def test_nasa_tile_is_the_user_guide_example_not_an_antofagasta_claim() -> None:
    for item in nasa_catalog():
        assert item["body"]["tile_id"] == "h08v05"
        assert "not an Antofagasta" in item["body"]["tile_id_source"]


def test_sentinel_has_documented_optical_bands_only() -> None:
    names = {band["name"] for band in S2_L2A_BANDS}
    assert names == {"B02", "B03", "B04", "B08"}
    item = sentinel_catalog()[0]
    assert item["body"]["collection"] == "sentinel-2-l2a"
    assert item["body"]["geometry"] is None
    assets = item["body"]["assets"]
    assert "DNB" not in assets
    assert item["body"]["night_lights_product"] is False
