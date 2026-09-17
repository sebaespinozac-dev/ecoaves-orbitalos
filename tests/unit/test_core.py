from __future__ import annotations

from pathlib import Path

from core.models import SOURCE_NASA_EARTHDATA
from core.orchestration import Orchestrator
from core.registry import AppRegistry
from core.reports import AppReport
from core.storage import Storage
from datahub.adapter import DiscoverCriteria
from simulators.memory import nasa_adapter


def test_storage_roundtrip_scene(tmp_path: Path) -> None:
    adapter = nasa_adapter()
    ref = list(adapter.discover(DiscoverCriteria(max_items=1)))[0]
    scene = adapter.normalize(adapter.fetch(ref))
    with Storage(tmp_path / "db.sqlite3") as storage:
        storage.save_scene(scene, batch_id="B")
        loaded = storage.scenes_for_batch("B")
    assert len(loaded) == 1
    assert loaded[0].provenance.source == SOURCE_NASA_EARTHDATA
    assert loaded[0].cite("black_marble_product")["provenance"]["granule_id"]


def test_orchestrator_ingests_injected_adapter(tmp_path: Path) -> None:
    storage = Storage(tmp_path / "db.sqlite3")
    orch = Orchestrator(
        storage=storage,
        adapters={SOURCE_NASA_EARTHDATA: nasa_adapter()},
        registry=AppRegistry(),
    )
    counts = orch.ingest(SOURCE_NASA_EARTHDATA, batch_id="B")
    assert counts["accepted"] >= 1
    assert counts["rejected"] == 0
    assert storage.scenes_for_batch("B")


class _StubApp:
    name = "stub"
    consumes_sources = frozenset({SOURCE_NASA_EARTHDATA})
    produces = frozenset({"stub.out"})

    def process(self, scenes, *, batch_id: str) -> AppReport:
        return AppReport(
            app=self.name,
            batch_id=batch_id,
            schema_version="stub.v1",
            generated_at_utc="2026-01-01T00:00:00Z",
            payload={"n": len(scenes)},
            summary_text=f"n={len(scenes)}",
        )


def test_registry_dispatches_without_knowing_darksky(tmp_path: Path) -> None:
    storage = Storage(tmp_path / "db.sqlite3")
    registry = AppRegistry()
    registry.register(_StubApp())
    orch = Orchestrator(
        storage=storage,
        adapters={SOURCE_NASA_EARTHDATA: nasa_adapter()},
        registry=registry,
    )
    orch.ingest(SOURCE_NASA_EARTHDATA, batch_id="B")
    report = orch.process_app("stub", batch_id="B")
    assert report.payload["n"] >= 1
    assert "darksky" not in registry.names()
