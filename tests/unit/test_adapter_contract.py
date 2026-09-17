from __future__ import annotations

import pytest

from core.models import (
    SOURCE_COPERNICUS_SENTINEL,
    SOURCE_CUBESAT_UA,
    SOURCE_NASA_EARTHDATA,
    SOURCES,
    Scene,
)
from datahub.adapter import DataHubAdapter, DiscoverCriteria
from simulators.memory import cubesat_adapter, nasa_adapter, sentinel_adapter


def _roundtrip(adapter: DataHubAdapter) -> list[Scene]:
    refs = list(adapter.discover(DiscoverCriteria(max_items=10)))
    scenes = []
    for ref in refs:
        payload = adapter.fetch(ref)
        assert payload.synthetic is True
        assert payload.ref.uri.startswith("fixture://")
        scene = adapter.normalize(payload)
        assert isinstance(scene, Scene)
        scenes.append(scene)
    return scenes


def test_each_synthetic_adapter_matches_protocol() -> None:
    adapters: list[DataHubAdapter] = [cubesat_adapter(), nasa_adapter(), sentinel_adapter()]
    seen = {adapter.source for adapter in adapters}
    assert seen == set(SOURCES)


def test_every_normalized_scene_has_full_provenance() -> None:
    required = {
        "source",
        "product_id",
        "granule_id",
        "acquisition_time",
        "retrieval_time",
        "license",
        "processing_level",
        "schema_version",
    }
    for adapter in (cubesat_adapter(), nasa_adapter(), sentinel_adapter()):
        for scene in _roundtrip(adapter):
            cited = scene.provenance.as_dict()
            assert set(cited) == required
            assert all(cited[key] for key in required)
            assert scene.provenance.source == adapter.source


def test_cubesat_scenes_are_not_georeferenced() -> None:
    adapter = cubesat_adapter()
    assert adapter.source == SOURCE_CUBESAT_UA
    for scene in _roundtrip(adapter):
        assert scene.georeferenced is False
        assert scene.spatial is None
        level = scene.cite("level")
        assert level["position_frame"] == "scene_relative"
        assert level["provenance"]["processing_level"] == "ua.blue_proxy.analysis.v1"


def test_nasa_discover_prioritizes_vj146_and_vj246() -> None:
    adapter = nasa_adapter()
    assert adapter.source == SOURCE_NASA_EARTHDATA
    refs = list(adapter.discover(DiscoverCriteria()))
    products = [ref.product_id for ref in refs]
    assert products[0] in {"VJ146A1", "VJ246A1"}
    assert products.index("VJ146A1") < products.index("VNP46A1")
    assert products.index("VJ246A1") < products.index("VNP46A1")


def test_sentinel_fixture_is_optical_not_night_lights() -> None:
    adapter = sentinel_adapter()
    assert adapter.source == SOURCE_COPERNICUS_SENTINEL
    scenes = _roundtrip(adapter)
    assert len(scenes) == 1
    scene = scenes[0]
    assert scene.cite("stac_collection")["value"] == "sentinel-2-l2a"
    assert scene.cite("night_lights_product")["value"] is False
    assert scene.payload["night_lights_product"] is False


def test_fetch_unknown_uri_fails_explicitly() -> None:
    from core.models import GranuleRef

    missing = GranuleRef(
        source=SOURCE_NASA_EARTHDATA,
        product_id="VJ146A1",
        granule_id="missing",
        uri="fixture://nasa_earthdata/does-not-exist",
        extra={},
    )
    with pytest.raises(KeyError):
        nasa_adapter().fetch(missing)
