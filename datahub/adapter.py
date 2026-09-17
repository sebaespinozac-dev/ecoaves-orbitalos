"""Contrato común de un adaptador de DataHub.

discover(criteria) -> list[GranuleRef]
fetch(ref) -> RawPayload
normalize(payload) -> Scene

Ningún adaptador abre el árbol interno del software de vuelo de la UA.
Las URLs operativas de NASA/Copernicus viven en cada adaptador (`endpoints.py`),
nunca en core. Este módulo no hace red.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Protocol, Sequence

from core.models import GranuleRef, Scene


@dataclass(frozen=True)
class DiscoverCriteria:
    time_start: Optional[str] = None
    time_end: Optional[str] = None
    bbox_wsen: Optional[tuple[float, float, float, float]] = None
    product_ids: tuple[str, ...] = ()
    max_items: int = 10
    extra: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RawPayload:
    ref: GranuleRef
    media_type: str
    body: Any
    retrieved_at: str
    synthetic: bool = False


class DataHubAdapter(Protocol):
    """Un adaptador = una fuente. Core no conoce NASA, Sentinel ni el CubeSat."""

    source: str

    def discover(self, criteria: DiscoverCriteria) -> Sequence[GranuleRef]:
        """Lista gránulos candidatos. En CI el transporte es grabado, nunca la API real."""

    def fetch(self, ref: GranuleRef) -> RawPayload:
        """Obtiene el payload bruto del locator en GranuleRef.uri."""

    def normalize(self, payload: RawPayload) -> Scene:
        """Convierte el payload a Scene con Provenance completa."""
