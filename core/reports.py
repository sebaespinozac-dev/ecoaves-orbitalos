"""Reporte de app con procedencia. Nada se cita sin Provenance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AppReport:
    app: str
    batch_id: str
    schema_version: str
    generated_at_utc: str
    payload: dict[str, Any]
    summary_text: str
