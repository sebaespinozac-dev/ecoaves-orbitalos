"""Modelo de datos propio de ECOAVES OrbitalOS.

Ninguna de estas clases es una entidad del software de vuelo de la UA.
Cada Scene lleva Provenance completa: core y apps no pueden citar un dato
sin saber de qué fuente, producto y gránulo salió.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

SOURCE_NASA_EARTHDATA = "nasa_earthdata"
SOURCE_COPERNICUS_SENTINEL = "copernicus_sentinel"
SOURCE_CUBESAT_UA = "cubesat_ua"

SOURCES = frozenset(
    {
        SOURCE_NASA_EARTHDATA,
        SOURCE_COPERNICUS_SENTINEL,
        SOURCE_CUBESAT_UA,
    }
)

# Esquema interno de Scene en este repositorio (independiente de cada emisor).
SCENE_SCHEMA_VERSION = "ecoaves_orbitalos.scene.v1"

# Productos Black Marble confirmados en LAADS / Earthdata (Collection 2).
# NASA deja de entregar Suomi NPP el 2026-11-01: VNP46 se deprioritiza.
NASA_BLACK_MARBLE_PREFERRED = ("VJ146A1", "VJ246A1")
NASA_BLACK_MARBLE_SUNSET = {
    "VNP46A1": "2026-11-01",
    "VNP46A2": "2026-11-01",
    "VNP46A3": "2026-11-01",
    "VNP46A4": "2026-11-01",
}

# Colección STAC CDSE confirmada. No hay producto Sentinel de luces nocturnas.
COPERNICUS_S2_L2A_COLLECTION = "sentinel-2-l2a"

UA_ANALYSIS_CONTRACT = "ua.blue_proxy.analysis.v1"


class ProvenanceError(ValueError):
    """Scene o GranuleRef sin procedencia usable."""


@dataclass(frozen=True)
class Provenance:
    source: str
    product_id: str
    granule_id: str
    acquisition_time: str
    retrieval_time: str
    license: str
    processing_level: str
    schema_version: str

    def __post_init__(self) -> None:
        _require_source(self.source)
        for field in (
            "product_id",
            "granule_id",
            "acquisition_time",
            "retrieval_time",
            "license",
            "processing_level",
            "schema_version",
        ):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise ProvenanceError(f"Provenance.{field} es obligatorio y no vacío")
        if self.schema_version != SCENE_SCHEMA_VERSION:
            raise ProvenanceError(
                f"schema_version no reconocido {self.schema_version!r}; "
                f"este hito solo admite {SCENE_SCHEMA_VERSION!r}"
            )

    def as_dict(self) -> dict[str, str]:
        return {
            "source": self.source,
            "product_id": self.product_id,
            "granule_id": self.granule_id,
            "acquisition_time": self.acquisition_time,
            "retrieval_time": self.retrieval_time,
            "license": self.license,
            "processing_level": self.processing_level,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class SpatialExtent:
    """Extensión geográfica solo cuando la fuente la declara.

    El CubeSat UA no tiene efemérides/actitud documentadas: spatial queda None.
    """

    crs: str
    bbox_wsen: tuple[float, float, float, float]
    note: str


@dataclass(frozen=True)
class Observation:
    """Dato citable dentro de una Scene. Siempre se lee junto a Scene.provenance."""

    name: str
    value: Any
    unit: Optional[str]
    position_frame: str


@dataclass(frozen=True)
class Scene:
    scene_id: str
    provenance: Provenance
    georeferenced: bool
    spatial: Optional[SpatialExtent]
    observations: tuple[Observation, ...]
    payload: Mapping[str, Any]
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.scene_id.strip():
            raise ProvenanceError("Scene.scene_id es obligatorio")
        if not isinstance(self.provenance, Provenance):
            raise ProvenanceError("Scene.provenance es obligatorio")
        if self.georeferenced is False and self.spatial is not None:
            raise ProvenanceError(
                "una Scene no geo-referenciada no puede llevar SpatialExtent"
            )
        object.__setattr__(self, "payload", dict(self.payload))

    def cite(self, observation_name: str) -> dict[str, Any]:
        """Empaqueta un dato con su procedencia. No hay cita huérfana."""
        match = [obs for obs in self.observations if obs.name == observation_name]
        if not match:
            raise KeyError(
                f"observación {observation_name!r} ausente en {self.scene_id}"
            )
        obs = match[0]
        return {
            "observation": obs.name,
            "value": obs.value,
            "unit": obs.unit,
            "position_frame": obs.position_frame,
            "provenance": self.provenance.as_dict(),
        }


@dataclass(frozen=True)
class GranuleRef:
    source: str
    product_id: str
    granule_id: str
    uri: str
    extra: Mapping[str, Any]

    def __post_init__(self) -> None:
        _require_source(self.source)
        if not self.product_id.strip() or not self.granule_id.strip():
            raise ProvenanceError("GranuleRef requiere product_id y granule_id")
        if not self.uri.strip():
            raise ProvenanceError("GranuleRef.uri es obligatorio (locator, no tiene que ser HTTP)")
        object.__setattr__(self, "extra", dict(self.extra))


def _require_source(source: str) -> None:
    if source not in SOURCES:
        raise ProvenanceError(
            f"source no reconocido {source!r}; admitidos: {sorted(SOURCES)}"
        )
