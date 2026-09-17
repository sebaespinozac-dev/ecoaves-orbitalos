"""Adaptador NASA Earthdata / Black Marble.

discover: CMR granules.umm_json (short_name).
fetch: RelatedUrls tipo GET DATA, con EARTHDATA_TOKEN si hace falta.
Prioriza VJ146A1 y VJ246A1. VNP46* solo si el caller lo pide (SNPP sunset 2026-11-01).

No parsea HDF-EOS5: un fetch binario queda como metadata_only.
"""

from __future__ import annotations

import os
from typing import Any, Mapping, Sequence

from core.clock import utc_now
from core.models import (
    NASA_BLACK_MARBLE_PREFERRED,
    NASA_BLACK_MARBLE_SUNSET,
    SCENE_SCHEMA_VERSION,
    SOURCE_NASA_EARTHDATA,
    GranuleRef,
    Observation,
    Provenance,
    Scene,
)
from datahub.adapter import DiscoverCriteria, RawPayload
from datahub.adapters.nasa_earthdata.endpoints import EARTHDATA_TOKEN_ENV, NasaEndpoints
from datahub.errors import IngestRejection, RejectionReason
from datahub.http import HttpTransport
from simulators.licenses import NASA_VJ146A1_LICENSE, NASA_VJ246A1_LICENSE, NASA_VNP46A1_LICENSE

LICENSES = {
    "VJ146A1": NASA_VJ146A1_LICENSE,
    "VJ246A1": NASA_VJ246A1_LICENSE,
    "VNP46A1": NASA_VNP46A1_LICENSE,
}


class NasaEarthdataAdapter:
    source = SOURCE_NASA_EARTHDATA

    def __init__(
        self,
        transport: HttpTransport,
        *,
        endpoints: NasaEndpoints | None = None,
        token_env: Mapping[str, str] | None = None,
    ) -> None:
        self.transport = transport
        self.endpoints = endpoints or NasaEndpoints.from_environ()
        self._env = dict(token_env or os.environ)

    def discover(self, criteria: DiscoverCriteria) -> Sequence[GranuleRef]:
        products = criteria.product_ids or NASA_BLACK_MARBLE_PREFERRED
        refs: list[GranuleRef] = []
        for short_name in products:
            if short_name.startswith("VNP") and short_name not in criteria.product_ids:
                continue
            params = {
                "short_name": short_name,
                "page_size": str(min(criteria.max_items, 100)),
            }
            if criteria.time_start and criteria.time_end:
                params["temporal"] = f"{criteria.time_start},{criteria.time_end}"
            if criteria.bbox_wsen:
                west, south, east, north = criteria.bbox_wsen
                params["bounding_box"] = f"{west},{south},{east},{north}"
            headers = {"Client-Id": self.endpoints.client_id}
            token = self._env.get(EARTHDATA_TOKEN_ENV)
            if token:
                headers["Authorization"] = f"Bearer {token}"
            response = self.transport.request(
                "GET",
                self.endpoints.cmr_granules,
                headers=headers,
                params=params,
            )
            payload = response.json()
            items = payload.get("items") or []
            for item in items:
                refs.append(_granule_ref(item, short_name))
        refs.sort(key=_prefer_key)
        return refs[: criteria.max_items]

    def fetch(self, ref: GranuleRef) -> RawPayload:
        if ref.source != self.source:
            raise IngestRejection(RejectionReason.PRODUCT_NOT_ALLOWED, f"source {ref.source}")
        data_url = str(ref.extra.get("data_url") or ref.uri)
        headers = {"Client-Id": self.endpoints.client_id}
        token = self._env.get(EARTHDATA_TOKEN_ENV)
        if token:
            headers["Authorization"] = f"Bearer {token}"
        response = self.transport.request("GET", data_url, headers=headers)
        body: Any
        media = response.headers.get("content-type", "application/octet-stream")
        if b"{" in response.body[:8] or media.startswith("application/json"):
            body = response.json()
            media = "application/json"
        else:
            body = {
                "bytes": len(response.body),
                "hdf_parsed": False,
                "note": "HDF-EOS5 not parsed in this MVP; DARKSKY uses granule metadata only",
            }
        return RawPayload(
            ref=ref,
            media_type=media,
            body=body,
            retrieved_at=utc_now(),
            synthetic=bool(ref.extra.get("synthetic")),
        )

    def normalize(self, payload: RawPayload) -> Scene:
        extra = payload.ref.extra
        product = payload.ref.product_id
        sunset = NASA_BLACK_MARBLE_SUNSET.get(product)
        warnings = [
            "Black Marble is georeferenced at 15 arc-second; this Scene omits tile bbox unless the granule provides it.",
            "Photometry SDS are not unpacked from HDF in this MVP (metadata_only).",
        ]
        if sunset:
            warnings.append(f"{product} Suomi NPP delivery ends {sunset}; prefer VJ146/VJ246.")
        body = payload.body if isinstance(payload.body, dict) else {"raw": "non-json"}
        return Scene(
            scene_id=f"{self.source}:{payload.ref.granule_id}",
            provenance=Provenance(
                source=self.source,
                product_id=product,
                granule_id=payload.ref.granule_id,
                acquisition_time=str(extra.get("acquisition_time") or payload.retrieved_at),
                retrieval_time=payload.retrieved_at,
                license=LICENSES.get(product, NASA_VJ146A1_LICENSE),
                processing_level="Level-3",
                schema_version=SCENE_SCHEMA_VERSION,
            ),
            georeferenced=True,
            spatial=None,
            observations=(
                Observation("black_marble_product", product, None, "geographic"),
                Observation("payload_kind", "metadata_only", None, "none"),
            ),
            payload={
                "short_name": product,
                "fetch": body,
                "platform": extra.get("platform"),
                "tile_id": extra.get("tile_id"),
            },
            warnings=tuple(warnings),
        )


def _granule_ref(item: Mapping[str, Any], short_name: str) -> GranuleRef:
    meta = item.get("meta") or {}
    umm = item.get("umm") or {}
    granule_id = str(
        umm.get("GranuleUR")
        or meta.get("native-id")
        or meta.get("concept-id")
        or ""
    )
    if not granule_id:
        raise IngestRejection(RejectionReason.SCHEMA_MISMATCH, "granulo CMR sin GranuleUR")
    temporal = ((umm.get("TemporalExtent") or {}).get("RangeDateTime") or {}).get("BeginningDateTime")
    data_url = _data_url(umm) or ""
    if not data_url:
        raise IngestRejection(RejectionReason.SCHEMA_MISMATCH, f"{granule_id}: sin RelatedUrls GET DATA")
    tile_id = None
    parts = granule_id.split(".")
    for part in parts:
        if part.startswith("h") and "v" in part and len(part) == 6:
            tile_id = part
            break
    return GranuleRef(
        source=SOURCE_NASA_EARTHDATA,
        product_id=short_name,
        granule_id=granule_id,
        uri=data_url,
        extra={
            "acquisition_time": temporal or "",
            "concept_id": meta.get("concept-id"),
            "tile_id": tile_id,
            "data_url": data_url,
            "platform": (umm.get("Platforms") or [{}])[0].get("ShortName") if umm.get("Platforms") else None,
            "recording_note": meta.get("recording_note"),
        },
    )


def _data_url(umm: Mapping[str, Any]) -> str | None:
    for related in umm.get("RelatedUrls") or ():
        if str(related.get("Type", "")).upper() == "GET DATA":
            return related.get("URL")
    return None


def _prefer_key(ref: GranuleRef) -> tuple[int, str]:
    rank = {name: index for index, name in enumerate(NASA_BLACK_MARBLE_PREFERRED)}
    return (rank.get(ref.product_id, 100), ref.granule_id)
