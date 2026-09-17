from __future__ import annotations

import pytest

from core.models import NASA_BLACK_MARBLE_PREFERRED
from datahub.adapter import DiscoverCriteria
from datahub.adapters.nasa_earthdata import NasaEarthdataAdapter
from datahub.http import UnexpectedHttpError
from tests.integration.http_recordings import nasa_recorded_transport


def test_nasa_discover_and_fetch_against_recordings() -> None:
    adapter = NasaEarthdataAdapter(nasa_recorded_transport())
    refs = list(adapter.discover(DiscoverCriteria()))
    products = [ref.product_id for ref in refs]
    assert products[0] in NASA_BLACK_MARBLE_PREFERRED
    assert "VNP46A1" not in products
    scene = adapter.normalize(adapter.fetch(refs[0]))
    assert scene.cite("black_marble_product")["value"] in {"VJ146A1", "VJ246A1"}
    assert scene.cite("payload_kind")["value"] == "metadata_only"
    assert scene.cite("black_marble_product")["provenance"]["source"] == "nasa_earthdata"


def test_nasa_does_not_hit_network_for_unknown_url() -> None:
    adapter = NasaEarthdataAdapter(nasa_recorded_transport())
    with pytest.raises(UnexpectedHttpError):
        adapter.discover(DiscoverCriteria(product_ids=("VNP46A1",)))
