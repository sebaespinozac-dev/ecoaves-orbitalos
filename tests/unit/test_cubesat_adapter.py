from __future__ import annotations

import json
from pathlib import Path

from datahub.adapter import DiscoverCriteria
from datahub.adapters.cubesat_ua import CubesatUaAdapter
from datahub.errors import IngestRejection, RejectionReason
from simulators.drop import write_cubesat_drop


def test_cubesat_adapter_reads_drop(tmp_path: Path) -> None:
    drop = write_cubesat_drop(tmp_path / "drop", batch_id="UA", profile="worsening")
    adapter = CubesatUaAdapter(drop)
    refs = list(adapter.discover(DiscoverCriteria()))
    assert len(refs) == 4
    scene = adapter.normalize(adapter.fetch(refs[0]))
    assert scene.georeferenced is False
    assert scene.cite("level")["provenance"]["source"] == "cubesat_ua"
    assert scene.cite("level")["position_frame"] == "scene_relative"


def test_cubesat_rejects_unknown_contract(tmp_path: Path) -> None:
    drop = write_cubesat_drop(tmp_path / "drop", batch_id="BAD", profile="stable")
    product = drop / "BAD-C001.analysis.product"
    payload = json.loads(product.read_text())
    payload["contract"] = "ua.something.else.v9"
    product.write_text(json.dumps(payload), encoding="utf-8")
    adapter = CubesatUaAdapter(drop)
    ref = next(r for r in adapter.discover(DiscoverCriteria()) if r.product_id == "BAD-C001")
    raw = adapter.fetch(ref)
    try:
        adapter.normalize(raw)
        raise AssertionError("debía rechazar")
    except IngestRejection as exc:
        assert exc.reason == RejectionReason.UNRECOGNIZED_CONTRACT
        assert "ua.something.else.v9" in str(exc)
