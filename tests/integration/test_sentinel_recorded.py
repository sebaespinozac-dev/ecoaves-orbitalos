from __future__ import annotations

from datahub.adapter import DiscoverCriteria
from datahub.adapters.copernicus_sentinel import CopernicusSentinelAdapter
from datahub.errors import IngestRejection, RejectionReason
from tests.integration.http_recordings import sentinel_recorded_transport


def test_sentinel_stac_roundtrip_recorded() -> None:
    adapter = CopernicusSentinelAdapter(sentinel_recorded_transport())
    refs = list(adapter.discover(DiscoverCriteria()))
    assert len(refs) == 1
    assert refs[0].product_id == "sentinel-2-l2a"
    scene = adapter.normalize(adapter.fetch(refs[0]))
    assert scene.cite("night_lights_product")["value"] is False
    assert scene.cite("stac_collection")["provenance"]["source"] == "copernicus_sentinel"


def test_sentinel_oauth_uses_recorded_token() -> None:
    adapter = CopernicusSentinelAdapter(
        sentinel_recorded_transport(with_oauth=True),
        token_env={"CDSE_CLIENT_ID": "ci", "CDSE_CLIENT_SECRET": "ci"},
    )
    refs = list(adapter.discover(DiscoverCriteria()))
    assert refs[0].granule_id == "FIXTURE-S2L2A-0001"


def test_sentinel_rejects_invented_night_lights_collection() -> None:
    adapter = CopernicusSentinelAdapter(sentinel_recorded_transport())
    try:
        adapter.discover(DiscoverCriteria(product_ids=("sentinel-night-lights",)))
        raise AssertionError("debía rechazar")
    except IngestRejection as exc:
        assert exc.reason == RejectionReason.PRODUCT_NOT_ALLOWED
