from __future__ import annotations

from datahub.adapter import DiscoverCriteria
from simulators.memory import nasa_adapter


def test_explicit_vnp46_still_discoverable_when_requested() -> None:
    refs = list(nasa_adapter().discover(DiscoverCriteria(product_ids=("VNP46A1",))))
    assert [ref.product_id for ref in refs] == ["VNP46A1"]
