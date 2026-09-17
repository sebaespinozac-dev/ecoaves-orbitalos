"""DARKSKY v0: NASA Black Marble (primaria) + CubeSat UA (opcional). Sentinel no entra."""

from __future__ import annotations

from statistics import mean
from typing import Any, Sequence

from core.clock import utc_now
from core.models import (
    SOURCE_COPERNICUS_SENTINEL,
    SOURCE_CUBESAT_UA,
    SOURCE_NASA_EARTHDATA,
    Scene,
)
from core.reports import AppReport

REPORT_SCHEMA = "ecoaves_orbitalos.darksky.report.v1"
LEVEL_RANK = {"normal": 0, "observar": 1, "fiscalizar": 2, "critico": 3}


class DarkskyApp:
    name = "darksky"
    consumes_sources = frozenset({SOURCE_NASA_EARTHDATA, SOURCE_CUBESAT_UA})
    produces = frozenset({"darksky.batch_report"})

    def process(self, scenes: Sequence[Scene], *, batch_id: str) -> AppReport:
        nasa = [s for s in scenes if s.provenance.source == SOURCE_NASA_EARTHDATA]
        ua = [s for s in scenes if s.provenance.source == SOURCE_CUBESAT_UA]
        ignored = [s for s in scenes if s.provenance.source == SOURCE_COPERNICUS_SENTINEL]
        nasa_block = _nasa_block(nasa)
        ua_block = _ua_block(ua)
        payload = {
            "app": self.name,
            "schema_version": REPORT_SCHEMA,
            "batch_id": batch_id,
            "generated_at_utc": utc_now(),
            "sources_used": sorted({s.provenance.source for s in nasa + ua}),
            "primary_source": SOURCE_NASA_EARTHDATA,
            "secondary_source": SOURCE_CUBESAT_UA,
            "sentinel_used": False,
            "sentinel_reason": (
                "No existe producto Sentinel equivalente a luces nocturnas VIIRS/Black Marble. "
                "El adaptador copernicus_sentinel está conectado al DataHub y testeado aislado, "
                "pero DARKSKY no lo consume."
            ),
            "sentinel_scenes_ignored": len(ignored),
            "nasa_earthdata": nasa_block,
            "cubesat_ua": ua_block,
            "geo_reference_note": (
                "NASA Black Marble sí está geo-referenciada (grilla lat/lon). "
                "El CubeSat UA no: celdas row/col relativas a la escena. "
                "Este reporte no inventa coordenadas para el CubeSat."
            ),
        }
        summary = _summary(payload)
        return AppReport(
            app=self.name,
            batch_id=batch_id,
            schema_version=REPORT_SCHEMA,
            generated_at_utc=payload["generated_at_utc"],
            payload=payload,
            summary_text=summary,
        )


def _nasa_block(scenes: Sequence[Scene]) -> dict[str, Any]:
    granules = []
    for scene in sorted(scenes, key=lambda item: item.provenance.acquisition_time):
        granules.append(
            {
                "product_id": scene.cite("black_marble_product"),
                "payload_kind": scene.cite("payload_kind"),
                "warnings": list(scene.warnings),
            }
        )
    return {
        "present": bool(scenes),
        "granule_count": len(scenes),
        "photometry": "unavailable_metadata_only",
        "photometry_note": (
            "VJ146A1/VJ246A1 contienen SDS de radiancia DNB en HDF-EOS5; este MVP no los "
            "desempaqueta. DARKSKY cita cobertura de gránulos, no un índice de brillo inventado."
        ),
        "granules": granules,
    }


def _ua_block(scenes: Sequence[Scene]) -> dict[str, Any]:
    ordered = sorted(scenes, key=lambda item: item.provenance.acquisition_time or item.provenance.granule_id)
    captures = []
    levels = []
    pcts = []
    for scene in ordered:
        level = scene.cite("level")
        pct = scene.cite("flagged_pct")
        cells = []
        for raw in scene.payload.get("cells") or ():
            cells.append(
                {
                    "row": raw["row"],
                    "col": raw["col"],
                    "blue_proxy": raw["blue_proxy"],
                    "flagged": raw["flagged"],
                    "position_frame": "scene_relative",
                    "geo_referenced": False,
                    "provenance": scene.provenance.as_dict(),
                }
            )
        captures.append(
            {
                "level": level,
                "flagged_pct": pct,
                "georeferenced": scene.georeferenced,
                "grid_cols": scene.payload.get("grid_cols"),
                "grid_rows": scene.payload.get("grid_rows"),
                "cells": cells,
            }
        )
        levels.append(level["value"])
        pcts.append(float(pct["value"]))
    trend = "insufficient_data"
    if len(levels) >= 2:
        delta_level = LEVEL_RANK.get(levels[-1], 0) - LEVEL_RANK.get(levels[0], 0)
        delta_pct = pcts[-1] - pcts[0]
        if delta_level > 0 or delta_pct >= 5:
            trend = "worsening"
        elif delta_level < 0 or delta_pct <= -5:
            trend = "improving"
        else:
            trend = "stable"
    return {
        "present": bool(scenes),
        "capture_count": len(scenes),
        "trend": trend,
        "mean_flagged_pct": round(mean(pcts), 4) if pcts else None,
        "peak_level": max(levels, key=lambda lv: LEVEL_RANK.get(lv, -1)) if levels else None,
        "geo_reference": None,
        "captures": captures,
    }


def _summary(payload: dict[str, Any]) -> str:
    nasa = payload["nasa_earthdata"]
    ua = payload["cubesat_ua"]
    lines = [
        f"DARKSKY lote {payload['batch_id']}",
        f"primaria: nasa_earthdata gránulos={nasa['granule_count']} fotometría={nasa['photometry']}",
        f"secundaria: cubesat_ua capturas={ua['capture_count']} tendencia={ua['trend']} pico={ua['peak_level']}",
        "sentinel: no usado (no hay producto de luces nocturnas)",
        payload["geo_reference_note"],
        "",
    ]
    for item in ua["captures"]:
        cited = item["flagged_pct"]["provenance"]
        lines.append(
            f"- UA {cited['granule_id']}: {item['level']['value']} "
            f"flagged_pct={item['flagged_pct']['value']} (scene_relative, source={cited['source']})"
        )
    for item in nasa["granules"]:
        cited = item["product_id"]["provenance"]
        lines.append(
            f"- NASA {cited['granule_id']}: product={item['product_id']['value']} "
            f"(source={cited['source']} license cited)"
        )
    return "\n".join(lines) + "\n"
