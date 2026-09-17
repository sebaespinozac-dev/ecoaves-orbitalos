"""Adaptadores sintéticos en memoria. Implementan DataHubAdapter sin red.

No son los adaptadores de datahub/adapters/ (hitos 2–4). Solo alimentan tests del Hito 0.
"""

from __future__ import annotations

from typing import Any, Sequence

from core.clock import utc_now
from core.models import (
    SOURCE_COPERNICUS_SENTINEL,
    SOURCE_CUBESAT_UA,
    SOURCE_NASA_EARTHDATA,
    NASA_BLACK_MARBLE_PREFERRED,
    SCENE_SCHEMA_VERSION,
    GranuleRef,
    Observation,
    Provenance,
    Scene,
)
from datahub.adapter import DiscoverCriteria, RawPayload
from simulators.copernicus_sentinel import sentinel_catalog
from simulators.cubesat_ua import cubesat_catalog
from simulators.nasa_earthdata import nasa_catalog


class SyntheticAdapter:
    def __init__(self, source: str, records: list[dict[str, Any]]) -> None:
        self.source = source
        self._records = {item["uri"]: item for item in records}
        self._order = [item["uri"] for item in records]

    def discover(self, criteria: DiscoverCriteria) -> Sequence[GranuleRef]:
        refs: list[GranuleRef] = []
        for uri in self._order:
            item = self._records[uri]
            if criteria.product_ids and item["product_id"] not in criteria.product_ids:
                continue
            refs.append(_ref(self.source, item))
        if self.source == SOURCE_NASA_EARTHDATA and not criteria.product_ids:
            refs.sort(key=lambda ref: _nasa_rank(ref.product_id))
        return refs[: criteria.max_items]

    def fetch(self, ref: GranuleRef) -> RawPayload:
        if ref.source != self.source:
            raise ValueError(f"{self.source} no sirve source={ref.source}")
        item = self._records.get(ref.uri)
        if item is None:
            raise KeyError(f"fixture no encontrada: {ref.uri}")
        return RawPayload(
            ref=ref,
            media_type=item["media_type"],
            body=item["body"],
            retrieved_at=utc_now(),
            synthetic=True,
        )

    def normalize(self, payload: RawPayload) -> Scene:
        item = self._records[payload.ref.uri]
        warnings = []
        if item.get("warning"):
            warnings.append(item["warning"])
        provenance = Provenance(
            source=self.source,
            product_id=item["product_id"],
            granule_id=item["granule_id"],
            acquisition_time=item["acquisition_time"],
            retrieval_time=payload.retrieved_at,
            license=item["license"],
            processing_level=item["processing_level"],
            schema_version=SCENE_SCHEMA_VERSION,
        )
        observations = _observations(self.source, item)
        return Scene(
            scene_id=f"{self.source}:{item['granule_id']}",
            provenance=provenance,
            georeferenced=bool(item["georeferenced"]),
            spatial=None,
            observations=observations,
            payload=item["body"],
            warnings=tuple(warnings),
        )


def cubesat_adapter() -> SyntheticAdapter:
    return SyntheticAdapter(SOURCE_CUBESAT_UA, cubesat_catalog())


def nasa_adapter() -> SyntheticAdapter:
    return SyntheticAdapter(SOURCE_NASA_EARTHDATA, nasa_catalog())


def sentinel_adapter() -> SyntheticAdapter:
    return SyntheticAdapter(SOURCE_COPERNICUS_SENTINEL, sentinel_catalog())


def _ref(source: str, item: dict[str, Any]) -> GranuleRef:
    return GranuleRef(
        source=source,
        product_id=item["product_id"],
        granule_id=item["granule_id"],
        uri=item["uri"],
        extra={"synthetic": True},
    )


def _nasa_rank(product_id: str) -> tuple[int, str]:
    preferred = {name: index for index, name in enumerate(NASA_BLACK_MARBLE_PREFERRED)}
    return (preferred.get(product_id, 100), product_id)


def _observations(source: str, item: dict[str, Any]) -> tuple[Observation, ...]:
    body = item["body"]
    if source == SOURCE_CUBESAT_UA:
        return (
            Observation(
                name="level",
                value=body.get("level"),
                unit=None,
                position_frame="scene_relative",
            ),
            Observation(
                name="flagged_pct",
                value=body.get("flagged_pct"),
                unit="percent",
                position_frame="scene_relative",
            ),
        )
    if source == SOURCE_NASA_EARTHDATA:
        return (
            Observation(
                name="black_marble_product",
                value=body["short_name"],
                unit=None,
                position_frame="geographic",
            ),
            Observation(
                name="payload_kind",
                value="metadata_only",
                unit=None,
                position_frame="none",
            ),
        )
    return (
        Observation(
            name="stac_collection",
            value=body.get("collection"),
            unit=None,
            position_frame="geographic",
        ),
        Observation(
            name="night_lights_product",
            value=False,
            unit=None,
            position_frame="none",
        ),
    )
