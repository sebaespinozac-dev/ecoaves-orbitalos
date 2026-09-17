"""Escribe un drop CubeSat sintético (artefactos publicados, no el software de vuelo)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from simulators.cubesat_ua import complete_analysis, dumps_product, sample_event

LEVELS = ("normal", "observar", "fiscalizar", "critico")


def write_cubesat_drop(drop_dir: str | Path, *, batch_id: str = "DEMO", profile: str = "worsening") -> Path:
    root = Path(drop_dir)
    root.mkdir(parents=True, exist_ok=True)
    levels = LEVELS if profile == "worsening" else tuple(reversed(LEVELS))
    if profile == "stable":
        levels = ("observar", "observar", "observar", "observar")
    origin = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = []
    for index, level in enumerate(levels, start=1):
        capture_id = f"{batch_id}-C{index:03d}"
        flagged = level != "normal"
        body = complete_analysis(capture_id=capture_id, level=level, flagged=flagged)
        (root / f"{capture_id}.analysis.product").write_text(dumps_product(body), encoding="utf-8")
        event = sample_event(capture_id)
        event["timestamp_utc"] = (origin + timedelta(minutes=index)).strftime("%Y-%m-%dT%H:%M:%SZ")
        events.append(json.dumps(event))
    (root / "events.jsonl").write_text("\n".join(events) + "\n", encoding="utf-8")
    return root
