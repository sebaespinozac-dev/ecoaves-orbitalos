"""Fixture CubeSat UA: artefactos publicados, no el software de vuelo.

El JSON calza el contrato ua.blue_proxy.analysis.v1 descrito en la especificación
verificada contra el emisor. No se copia código de ese repositorio.
"""

from __future__ import annotations

import json
from typing import Any

from core.models import UA_ANALYSIS_CONTRACT
from simulators.licenses import CUBESAT_UA_LICENSE

GRID_COLS = 8
GRID_ROWS = 6

# Ejemplo literal del contrato publicado (1 celda ilustrativa, grilla 8x6).
SCHEMA_SAMPLE_ANALYSIS: dict[str, Any] = {
    "contract": UA_ANALYSIS_CONTRACT,
    "grid_cols": 8,
    "grid_rows": 6,
    "flagged_pct": 100.0,
    "level": "critico",
    "cells": [
        {
            "row": 0,
            "col": 0,
            "blue_proxy": 0.6154,
            "bg_ratio": 3.6667,
            "br_ratio": 4.4,
            "saturation": 0.7727,
            "brightness": 110.0,
            "clipped": False,
            "flagged": True,
        }
    ],
}


def complete_analysis(*, capture_id: str, level: str, flagged: bool) -> dict[str, Any]:
    """Grilla completa 8x6 generada aquí, no tomada de fixtures del emisor."""
    targets = {"normal": 0, "observar": 12, "fiscalizar": 28, "critico": 44}
    flagged_target = targets[level] if flagged else 0
    cells = []
    flagged_count = 0
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            is_flagged = (row * GRID_COLS + col) < flagged_target
            flagged_count += int(is_flagged)
            cells.append(
                {
                    "row": row,
                    "col": col,
                    "blue_proxy": 0.51 if is_flagged else 0.11,
                    "bg_ratio": 2.4 if is_flagged else 0.8,
                    "br_ratio": 2.8 if is_flagged else 0.9,
                    "saturation": 0.6 if is_flagged else 0.2,
                    "brightness": 100.0 if is_flagged else 70.0,
                    "clipped": False,
                    "flagged": is_flagged,
                }
            )
    total = GRID_COLS * GRID_ROWS
    return {
        "contract": UA_ANALYSIS_CONTRACT,
        "grid_cols": GRID_COLS,
        "grid_rows": GRID_ROWS,
        "flagged_pct": round(100.0 * flagged_count / total, 4),
        "level": level,
        "cells": cells,
        "capture_id": capture_id,
    }


def sample_event(capture_id: str) -> dict[str, Any]:
    return {
        "timestamp_utc": "2026-01-01T00:01:00Z",
        "capture_id": capture_id,
        "service": "drop_simulator",
        "stage": "published",
        "resulting_state": "drop_ready",
        "error_code": "NONE",
        "detail": "synthetic published artifact",
    }


def cubesat_catalog() -> list[dict[str, Any]]:
    complete = complete_analysis(capture_id="CAP001", level="observar", flagged=True)
    return [
        {
            "granule_id": "CAP001.analysis.product",
            "product_id": "CAP001",
            "uri": "fixture://cubesat_ua/CAP001.analysis.product",
            "acquisition_time": "2026-01-01T00:00:00Z",
            "license": CUBESAT_UA_LICENSE,
            "processing_level": UA_ANALYSIS_CONTRACT,
            "media_type": "application/json",
            "body": complete,
            "event": sample_event("CAP001"),
            "kind": "analysis",
            "georeferenced": False,
        },
        {
            "granule_id": "schema-sample.analysis.product",
            "product_id": "schema-sample",
            "uri": "fixture://cubesat_ua/schema-sample.analysis.product",
            "acquisition_time": "2026-01-01T00:00:00Z",
            "license": CUBESAT_UA_LICENSE,
            "processing_level": UA_ANALYSIS_CONTRACT,
            "media_type": "application/json",
            "body": SCHEMA_SAMPLE_ANALYSIS,
            "event": sample_event("schema-sample"),
            "kind": "analysis",
            "georeferenced": False,
            "warning": (
                "schema sample from the published contract illustration; "
                "cell count is not grid_cols*grid_rows"
            ),
        },
    ]


def dumps_product(body: dict[str, Any]) -> str:
    return json.dumps(body, indent=2) + "\n"
