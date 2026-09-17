"""Storage y lineage propios. Separado de catálogos NASA, CDSE y del SQLite de vuelo UA."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

from core.models import (
    SOURCE_CUBESAT_UA,
    SOURCE_NASA_EARTHDATA,
    SOURCE_COPERNICUS_SENTINEL,
    GranuleRef,
    Observation,
    Provenance,
    Scene,
    SpatialExtent,
)
from core.reports import AppReport

SCHEMA = """
CREATE TABLE IF NOT EXISTS scenes (
    scene_id TEXT PRIMARY KEY,
    batch_id TEXT NOT NULL,
    source TEXT NOT NULL,
    product_id TEXT NOT NULL,
    granule_id TEXT NOT NULL,
    provenance_json TEXT NOT NULL,
    georeferenced INTEGER NOT NULL,
    spatial_json TEXT,
    observations_json TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    warnings_json TEXT NOT NULL,
    ingested_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rejections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT NOT NULL,
    source TEXT NOT NULL,
    uri TEXT NOT NULL,
    reason TEXT NOT NULL,
    detail TEXT NOT NULL,
    rejected_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    app TEXT NOT NULL,
    batch_id TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    generated_at_utc TEXT NOT NULL,
    report_json TEXT NOT NULL,
    summary_text TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_scenes_batch ON scenes(batch_id, source);
"""


class Storage:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "Storage":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def save_scene(self, scene: Scene, *, batch_id: str) -> None:
        spatial = None
        if scene.spatial is not None:
            spatial = {
                "crs": scene.spatial.crs,
                "bbox_wsen": list(scene.spatial.bbox_wsen),
                "note": scene.spatial.note,
            }
        observations = [
            {
                "name": obs.name,
                "value": obs.value,
                "unit": obs.unit,
                "position_frame": obs.position_frame,
            }
            for obs in scene.observations
        ]
        self._conn.execute(
            """
            INSERT OR REPLACE INTO scenes (
                scene_id, batch_id, source, product_id, granule_id,
                provenance_json, georeferenced, spatial_json, observations_json,
                payload_json, warnings_json, ingested_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scene.scene_id,
                batch_id,
                scene.provenance.source,
                scene.provenance.product_id,
                scene.provenance.granule_id,
                json.dumps(scene.provenance.as_dict()),
                1 if scene.georeferenced else 0,
                json.dumps(spatial) if spatial else None,
                json.dumps(observations),
                json.dumps(scene.payload, default=str),
                json.dumps(list(scene.warnings)),
                scene.provenance.retrieval_time,
            ),
        )
        self._conn.commit()

    def save_rejection(
        self,
        *,
        batch_id: str,
        source: str,
        uri: str,
        reason: str,
        detail: str,
        rejected_at_utc: str,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO rejections (batch_id, source, uri, reason, detail, rejected_at_utc)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (batch_id, source, uri, reason, detail, rejected_at_utc),
        )
        self._conn.commit()

    def save_report(self, report: AppReport) -> None:
        self._conn.execute(
            """
            INSERT INTO reports (app, batch_id, schema_version, generated_at_utc, report_json, summary_text)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                report.app,
                report.batch_id,
                report.schema_version,
                report.generated_at_utc,
                json.dumps(report.payload, ensure_ascii=False, indent=2),
                report.summary_text,
            ),
        )
        self._conn.commit()

    def scenes_for_batch(self, batch_id: str, *, sources: Optional[frozenset[str]] = None) -> list[Scene]:
        rows = self._conn.execute(
            """
            SELECT scene_id, source, product_id, granule_id, provenance_json, georeferenced,
                   spatial_json, observations_json, payload_json, warnings_json
            FROM scenes WHERE batch_id = ? ORDER BY source, granule_id
            """,
            (batch_id,),
        ).fetchall()
        scenes: list[Scene] = []
        for row in rows:
            if sources is not None and row["source"] not in sources:
                continue
            scenes.append(_scene_from_row(row))
        return scenes

    def rejections_for_batch(self, batch_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT source, uri, reason, detail FROM rejections WHERE batch_id = ? ORDER BY id",
            (batch_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def latest_report(self, app: str, batch_id: str) -> Optional[AppReport]:
        row = self._conn.execute(
            """
            SELECT app, batch_id, schema_version, generated_at_utc, report_json, summary_text
            FROM reports WHERE app = ? AND batch_id = ? ORDER BY id DESC LIMIT 1
            """,
            (app, batch_id),
        ).fetchone()
        if row is None:
            return None
        return AppReport(
            app=row["app"],
            batch_id=row["batch_id"],
            schema_version=row["schema_version"],
            generated_at_utc=row["generated_at_utc"],
            payload=json.loads(row["report_json"]),
            summary_text=row["summary_text"],
        )


def _scene_from_row(row: sqlite3.Row) -> Scene:
    prov = Provenance(**json.loads(row["provenance_json"]))
    spatial = None
    if row["spatial_json"]:
        raw = json.loads(row["spatial_json"])
        spatial = SpatialExtent(
            crs=raw["crs"],
            bbox_wsen=tuple(raw["bbox_wsen"]),
            note=raw["note"],
        )
    observations = tuple(
        Observation(
            name=item["name"],
            value=item["value"],
            unit=item["unit"],
            position_frame=item["position_frame"],
        )
        for item in json.loads(row["observations_json"])
    )
    return Scene(
        scene_id=row["scene_id"],
        provenance=prov,
        georeferenced=bool(row["georeferenced"]),
        spatial=spatial,
        observations=observations,
        payload=json.loads(row["payload_json"]),
        warnings=tuple(json.loads(row["warnings_json"])),
    )


# Re-export source constants so tests can see storage is source-agnostic at import time.
KNOWN_SOURCES = (SOURCE_NASA_EARTHDATA, SOURCE_COPERNICUS_SENTINEL, SOURCE_CUBESAT_UA)

__all__ = ["Storage", "KNOWN_SOURCES", "GranuleRef"]
