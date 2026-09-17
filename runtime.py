"""Composición: las tres fuentes conectadas al Core. DARKSKY no usa Sentinel."""

from __future__ import annotations

from pathlib import Path

from apps import default_registry
from core.orchestration import Orchestrator
from core.storage import Storage
from datahub.adapters.copernicus_sentinel import CopernicusSentinelAdapter
from datahub.adapters.cubesat_ua import CubesatUaAdapter
from datahub.adapters.nasa_earthdata import NasaEarthdataAdapter
from datahub.http import HttpTransport


def build_orchestrator(
    *,
    db_path: str | Path,
    drop_dir: str | Path,
    nasa_transport: HttpTransport,
    sentinel_transport: HttpTransport,
) -> Orchestrator:
    adapters = {
        "cubesat_ua": CubesatUaAdapter(drop_dir),
        "nasa_earthdata": NasaEarthdataAdapter(nasa_transport),
        "copernicus_sentinel": CopernicusSentinelAdapter(sentinel_transport),
    }
    return Orchestrator(
        storage=Storage(db_path),
        adapters=adapters,
        registry=default_registry(),
    )
