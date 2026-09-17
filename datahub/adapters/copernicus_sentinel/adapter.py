"""Adaptador Copernicus Sentinel (STAC + OAuth Sentinel Hub).

Discover: STAC POST search, colección sentinel-2-l2a.
Fetch: STAC item (catálogo). Pixel fetch vía Sentinel Hub Process queda opt-in y
NO se usa en DARKSKY: no hay producto Sentinel de luces nocturnas.

Este adaptador se prueba aislado y se puede ingerir al DataHub; DARKSKY lo ignora.
"""

from __future__ import annotations

import os
from typing import Any, Mapping, Sequence

from core.clock import utc_now
from core.models import (
    COPERNICUS_S2_L2A_COLLECTION,
    SCENE_SCHEMA_VERSION,
    SOURCE_COPERNICUS_SENTINEL,
    GranuleRef,
    Observation,
    Provenance,
    Scene,
)
from datahub.adapter import DiscoverCriteria, RawPayload
from datahub.adapters.copernicus_sentinel.endpoints import (
    CDSE_CLIENT_ID_ENV,
    CDSE_CLIENT_SECRET_ENV,
    CopernicusEndpoints,
)
from datahub.errors import IngestRejection, RejectionReason
from datahub.http import HttpTransport
from simulators.licenses import COPERNICUS_SENTINEL_LICENSE


class CopernicusSentinelAdapter:
    source = SOURCE_COPERNICUS_SENTINEL

    def __init__(
        self,
        transport: HttpTransport,
        *,
        endpoints: CopernicusEndpoints | None = None,
        token_env: Mapping[str, str] | None = None,
    ) -> None:
        self.transport = transport
        self.endpoints = endpoints or CopernicusEndpoints.from_environ()
        self._env = dict(token_env or os.environ)
        self._token: str | None = None

    def discover(self, criteria: DiscoverCriteria) -> Sequence[GranuleRef]:
        collections = list(criteria.product_ids) or [COPERNICUS_S2_L2A_COLLECTION]
        if any("night" in name.lower() or "dnb" in name.lower() or "viirs" in name.lower() for name in collections):
            raise IngestRejection(
                RejectionReason.PRODUCT_NOT_ALLOWED,
                "no hay producto Sentinel de luces nocturnas; no se inventa esa colección",
            )
        body: dict[str, Any] = {"collections": collections, "limit": criteria.max_items}
        if criteria.time_start and criteria.time_end:
            body["datetime"] = f"{criteria.time_start}/{criteria.time_end}"
        if criteria.bbox_wsen:
            body["bbox"] = list(criteria.bbox_wsen)
        headers = {"Accept": "application/geo+json"}
        token = self._oauth_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        response = self.transport.request(
            "POST",
            self.endpoints.stac_search,
            headers=headers,
            json_body=body,
        )
        payload = response.json()
        refs: list[GranuleRef] = []
        for feature in payload.get("features") or ():
            refs.append(_item_ref(feature))
        return refs[: criteria.max_items]

    def fetch(self, ref: GranuleRef) -> RawPayload:
        headers = {"Accept": "application/geo+json"}
        token = self._oauth_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        item_url = str(ref.extra.get("self_href") or ref.uri)
        response = self.transport.request("GET", item_url, headers=headers)
        return RawPayload(
            ref=ref,
            media_type="application/geo+json",
            body=response.json(),
            retrieved_at=utc_now(),
            synthetic=bool(ref.extra.get("synthetic")),
        )

    def normalize(self, payload: RawPayload) -> Scene:
        item = payload.body if isinstance(payload.body, dict) else {}
        collection = item.get("collection") or payload.ref.product_id
        props = item.get("properties") or {}
        return Scene(
            scene_id=f"{self.source}:{payload.ref.granule_id}",
            provenance=Provenance(
                source=self.source,
                product_id=collection,
                granule_id=payload.ref.granule_id,
                acquisition_time=str(props.get("datetime") or payload.ref.extra.get("datetime") or payload.retrieved_at),
                retrieval_time=payload.retrieved_at,
                license=COPERNICUS_SENTINEL_LICENSE,
                processing_level=str(props.get("processing:level") or "L2A"),
                schema_version=SCENE_SCHEMA_VERSION,
            ),
            georeferenced=True,
            spatial=None,
            observations=(
                Observation("stac_collection", collection, None, "geographic"),
                Observation("night_lights_product", False, None, "none"),
            ),
            payload=item,
            warnings=(
                "Sentinel-2 L2A is optical surface reflectance, not VIIRS DNB. "
                "DARKSKY does not consume this source.",
                "Pixel fetch via Sentinel Hub Process API is not invoked in this MVP (processing units).",
            ),
        )

    def _oauth_token(self) -> str | None:
        if self._token:
            return self._token
        client_id = self._env.get(CDSE_CLIENT_ID_ENV)
        client_secret = self._env.get(CDSE_CLIENT_SECRET_ENV)
        if not client_id or not client_secret:
            return None
        response = self.transport.request(
            "POST",
            self.endpoints.oauth_token,
            form={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
        )
        token = response.json().get("access_token")
        if not isinstance(token, str) or not token:
            raise IngestRejection(RejectionReason.AUTH_MISSING, "OAuth CDSE sin access_token")
        self._token = token
        return token


def _item_ref(feature: Mapping[str, Any]) -> GranuleRef:
    item_id = str(feature.get("id") or "")
    collection = str(feature.get("collection") or COPERNICUS_S2_L2A_COLLECTION)
    if not item_id:
        raise IngestRejection(RejectionReason.SCHEMA_MISMATCH, "STAC item sin id")
    self_href = None
    for link in feature.get("links") or ():
        if link.get("rel") == "self":
            self_href = link.get("href")
            break
    uri = self_href or f"stac://{collection}/{item_id}"
    props = feature.get("properties") or {}
    return GranuleRef(
        source=SOURCE_COPERNICUS_SENTINEL,
        product_id=collection,
        granule_id=item_id,
        uri=uri,
        extra={
            "datetime": props.get("datetime"),
            "self_href": self_href or uri,
            "synthetic": bool(feature.get("synthetic")),
        },
    )
