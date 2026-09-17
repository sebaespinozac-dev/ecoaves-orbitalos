"""Adaptador cubesat_ua: solo lee un drop de artefactos ya publicados."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Optional, Sequence

from core.clock import utc_now
from core.models import (
    SCENE_SCHEMA_VERSION,
    SOURCE_CUBESAT_UA,
    UA_ANALYSIS_CONTRACT,
    GranuleRef,
    Observation,
    Provenance,
    Scene,
)
from datahub.adapter import DiscoverCriteria, RawPayload
from datahub.errors import IngestRejection, RejectionReason
from simulators.licenses import CUBESAT_UA_LICENSE

LOGGER = logging.getLogger("ecoaves_orbitalos.cubesat_ua")

KIND_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
JSON_KINDS = frozenset({"analysis", "metrics", "product"})
KNOWN_KINDS = JSON_KINDS | frozenset({"grid", "heatmap"})
LEVELS = frozenset({"normal", "observar", "fiscalizar", "critico"})
EVENT_KEYS = (
    "timestamp_utc",
    "capture_id",
    "service",
    "stage",
    "resulting_state",
    "error_code",
    "detail",
)
ERROR_CODES = frozenset(
    {
        "NONE",
        "CAMERA_TIMEOUT",
        "CAPTURE_INCOMPLETE",
        "INPUT_CORRUPT",
        "PROCESSING_ERROR",
        "PROCESS_INTERRUPTED",
        "SYSTEM_RESTARTED",
        "STORAGE_FULL",
        "WRITE_INTERRUPTED",
        "TRANSFER_INTERRUPTED",
        "COMMUNICATION_TIMEOUT",
        "DUPLICATE_CONFLICT",
        "INTEGRITY_MISMATCH",
        "OBC_RESTARTED",
        "TEMPORARY_QUARANTINED",
        "INVALID_TRANSITION",
        "NOT_FOUND",
        "HARDWARE_UNAVAILABLE",
        "CONTRACT_VIOLATION",
        "COMMAND_REJECTED",
        "POWER_CONTROL_ERROR",
        "HEARTBEAT_FAILED",
        "RAW_UNAVAILABLE",
        "INTERNAL_ERROR",
    }
)
CELL_FIELDS = (
    "row",
    "col",
    "blue_proxy",
    "bg_ratio",
    "br_ratio",
    "saturation",
    "brightness",
    "clipped",
    "flagged",
)


class CubesatUaAdapter:
    source = SOURCE_CUBESAT_UA

    def __init__(self, drop_dir: str | Path) -> None:
        self.drop_dir = Path(drop_dir)

    def discover(self, criteria: DiscoverCriteria) -> Sequence[GranuleRef]:
        if not self.drop_dir.is_dir():
            raise FileNotFoundError(f"drop no es un directorio: {self.drop_dir}")
        refs: list[GranuleRef] = []
        for path in sorted(self.drop_dir.iterdir()):
            if not path.is_file() or path.name == "events.jsonl" or path.name.startswith("."):
                continue
            try:
                capture_id, kind = parse_product_filename(path.name)
            except IngestRejection:
                LOGGER.error("RECHAZO archivo fuera de contrato drop file=%s", path.name)
                continue
            if kind not in JSON_KINDS:
                continue
            if criteria.product_ids and capture_id not in criteria.product_ids:
                continue
            refs.append(
                GranuleRef(
                    source=self.source,
                    product_id=capture_id,
                    granule_id=path.name,
                    uri=str(path.resolve()),
                    extra={"kind": kind, "drop_dir": str(self.drop_dir)},
                )
            )
        return refs[: criteria.max_items]

    def fetch(self, ref: GranuleRef) -> RawPayload:
        path = Path(ref.uri)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise IngestRejection(RejectionReason.SCHEMA_MISMATCH, f"no se pudo leer {path}: {exc}") from exc
        return RawPayload(
            ref=ref,
            media_type="application/json",
            body=text,
            retrieved_at=utc_now(),
            synthetic=False,
        )

    def normalize(self, payload: RawPayload) -> Scene:
        source = payload.ref.granule_id
        try:
            data = json.loads(payload.body) if isinstance(payload.body, str) else payload.body
        except json.JSONDecodeError as exc:
            raise IngestRejection(RejectionReason.SCHEMA_MISMATCH, f"{source}: JSON inválido ({exc})") from exc
        if not isinstance(data, dict):
            raise IngestRejection(RejectionReason.SCHEMA_MISMATCH, f"{source}: se esperaba objeto JSON")
        validated = validate_analysis(data, source=source)
        provenance = Provenance(
            source=self.source,
            product_id=payload.ref.product_id,
            granule_id=payload.ref.granule_id,
            acquisition_time=_event_time(self.drop_dir, payload.ref.product_id) or payload.retrieved_at,
            retrieval_time=payload.retrieved_at,
            license=CUBESAT_UA_LICENSE,
            processing_level=UA_ANALYSIS_CONTRACT,
            schema_version=SCENE_SCHEMA_VERSION,
        )
        return Scene(
            scene_id=f"{self.source}:{payload.ref.product_id}",
            provenance=provenance,
            georeferenced=False,
            spatial=None,
            observations=(
                Observation("level", validated["level"], None, "scene_relative"),
                Observation("flagged_pct", validated["flagged_pct"], "percent", "scene_relative"),
            ),
            payload=validated,
            warnings=(
                "CubeSat UA: sin efemérides/actitud documentadas; posiciones row/col relativas a la escena.",
            ),
        )


def parse_product_filename(filename: str) -> tuple[str, str]:
    if not filename.endswith(".product") or "/" in filename:
        raise IngestRejection(RejectionReason.INVALID_FILENAME, f"{filename}: no es *.product")
    stem = filename[: -len(".product")]
    if "." not in stem:
        kind = "product"
        capture_id = stem
    else:
        capture_id, kind = stem.rsplit(".", 1)
    if not capture_id or not KIND_RE.fullmatch(kind):
        raise IngestRejection(RejectionReason.INVALID_FILENAME, f"{filename}: capture_id/kind inválidos")
    if kind not in KNOWN_KINDS:
        raise IngestRejection(
            RejectionReason.UNRECOGNIZED_KIND,
            f"{filename}: kind no reconocido {kind!r}",
        )
    return capture_id, kind


def validate_analysis(payload: dict[str, Any], *, source: str) -> dict[str, Any]:
    contract = payload.get("contract")
    if not isinstance(contract, str) or not contract:
        raise IngestRejection(RejectionReason.SCHEMA_MISMATCH, f"{source}: falta contract")
    if contract != UA_ANALYSIS_CONTRACT:
        raise IngestRejection(
            RejectionReason.UNRECOGNIZED_CONTRACT,
            f"{source}: contract no reconocido {contract!r}; solo {UA_ANALYSIS_CONTRACT!r}",
        )
    cols = payload.get("grid_cols")
    rows = payload.get("grid_rows")
    if not isinstance(cols, int) or not isinstance(rows, int) or isinstance(cols, bool) or isinstance(rows, bool):
        raise IngestRejection(RejectionReason.SCHEMA_MISMATCH, f"{source}: grid_cols/grid_rows deben ser int")
    if cols < 1 or rows < 1:
        raise IngestRejection(RejectionReason.SCHEMA_MISMATCH, f"{source}: grilla inválida")
    flagged_pct = payload.get("flagged_pct")
    if isinstance(flagged_pct, bool) or not isinstance(flagged_pct, (int, float)):
        raise IngestRejection(RejectionReason.SCHEMA_MISMATCH, f"{source}: flagged_pct numérico")
    level = payload.get("level")
    if level not in LEVELS:
        raise IngestRejection(RejectionReason.SCHEMA_MISMATCH, f"{source}: level inválido {level!r}")
    cells = payload.get("cells")
    if not isinstance(cells, list) or len(cells) != cols * rows:
        raise IngestRejection(
            RejectionReason.SCHEMA_MISMATCH,
            f"{source}: se esperaban {cols * rows} celdas, hay {0 if not isinstance(cells, list) else len(cells)}",
        )
    for index, cell in enumerate(cells):
        if not isinstance(cell, dict) or any(field not in cell for field in CELL_FIELDS):
            raise IngestRejection(RejectionReason.SCHEMA_MISMATCH, f"{source} cells[{index}]: campos incompletos")
    return {
        "contract": contract,
        "grid_cols": cols,
        "grid_rows": rows,
        "flagged_pct": float(flagged_pct),
        "level": level,
        "cells": cells,
    }


def _event_time(drop_dir: Path, capture_id: str) -> Optional[str]:
    events = drop_dir / "events.jsonl"
    if not events.is_file():
        return None
    for line_no, line in enumerate(events.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            LOGGER.error("RECHAZO events.jsonl:%s JSON inválido", line_no)
            continue
        if not isinstance(item, dict) or set(item.keys()) != set(EVENT_KEYS):
            LOGGER.error("RECHAZO events.jsonl:%s claves no exactas", line_no)
            continue
        if item.get("error_code") not in ERROR_CODES:
            LOGGER.error("RECHAZO events.jsonl:%s error_code no reconocido", line_no)
            continue
        if item.get("capture_id") == capture_id and isinstance(item.get("timestamp_utc"), str):
            return item["timestamp_utc"]
    return None
