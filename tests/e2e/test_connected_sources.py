from __future__ import annotations

from pathlib import Path

from core.models import SOURCE_COPERNICUS_SENTINEL, SOURCE_CUBESAT_UA, SOURCE_NASA_EARTHDATA
from datahub.adapter import DiscoverCriteria
from runtime import build_orchestrator
from simulators.drop import write_cubesat_drop
from tests.integration.http_recordings import nasa_recorded_transport, sentinel_recorded_transport


def test_e2e_three_sources_darksky_skips_sentinel(tmp_path: Path) -> None:
    drop = write_cubesat_drop(tmp_path / "drop", batch_id="E2E", profile="worsening")
    orch = build_orchestrator(
        db_path=tmp_path / "satelital.sqlite3",
        drop_dir=drop,
        nasa_transport=nasa_recorded_transport(),
        sentinel_transport=sentinel_recorded_transport(),
    )
    counts = orch.ingest_sources(
        [SOURCE_NASA_EARTHDATA, SOURCE_CUBESAT_UA, SOURCE_COPERNICUS_SENTINEL],
        batch_id="E2E",
        criteria_by_source={
            SOURCE_NASA_EARTHDATA: DiscoverCriteria(),
            SOURCE_CUBESAT_UA: DiscoverCriteria(),
            SOURCE_COPERNICUS_SENTINEL: DiscoverCriteria(),
        },
    )
    assert counts[SOURCE_NASA_EARTHDATA]["accepted"] >= 1
    assert counts[SOURCE_CUBESAT_UA]["accepted"] == 4
    assert counts[SOURCE_COPERNICUS_SENTINEL]["accepted"] == 1
    assert all(item["rejected"] == 0 for item in counts.values())

    stored = orch.storage.scenes_for_batch("E2E")
    assert {s.provenance.source for s in stored} == {
        SOURCE_NASA_EARTHDATA,
        SOURCE_CUBESAT_UA,
        SOURCE_COPERNICUS_SENTINEL,
    }

    report = orch.process_app("darksky", batch_id="E2E")
    assert report.payload["sentinel_used"] is False
    assert SOURCE_COPERNICUS_SENTINEL not in report.payload["sources_used"]
    assert SOURCE_NASA_EARTHDATA in report.payload["sources_used"]
    assert SOURCE_CUBESAT_UA in report.payload["sources_used"]
    assert report.payload["cubesat_ua"]["trend"] == "worsening"
    assert report.payload["nasa_earthdata"]["photometry"] == "unavailable_metadata_only"
    ua_cite = report.payload["cubesat_ua"]["captures"][0]["level"]["provenance"]
    assert ua_cite["source"] == SOURCE_CUBESAT_UA
    nasa_cite = report.payload["nasa_earthdata"]["granules"][0]["product_id"]["provenance"]
    assert nasa_cite["license"]
    stored_report = orch.storage.latest_report("darksky", "E2E")
    assert stored_report is not None
    assert stored_report.payload["cubesat_ua"]["captures"][-1]["cells"]
    orch.storage.close()
