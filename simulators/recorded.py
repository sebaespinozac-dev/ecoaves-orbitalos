"""Transportes grabados reutilizables (CI y demo offline). Cero red."""

from __future__ import annotations

import json
from pathlib import Path

from datahub.adapters.copernicus_sentinel.endpoints import CopernicusEndpoints
from datahub.adapters.nasa_earthdata.endpoints import NasaEndpoints
from datahub.http import HttpResponse, RecordedTransport

ROOT = Path(__file__).resolve().parents[1]
RECORDINGS = ROOT / "tests" / "integration" / "recordings"


def _json_response(url: str, filename: str) -> HttpResponse:
    body = (RECORDINGS / filename).read_bytes()
    json.loads(body.decode("utf-8"))
    return HttpResponse(
        status=200,
        url=url,
        headers={"content-type": "application/json"},
        body=body,
    )


def nasa_recorded_transport() -> RecordedTransport:
    nasa = NasaEndpoints()
    return RecordedTransport(
        {
            ("GET", nasa.cmr_granules + "|short_name=VJ146A1"): _json_response(
                nasa.cmr_granules, "cmr_vj146a1.json"
            ),
            ("GET", nasa.cmr_granules + "|short_name=VJ246A1"): _json_response(
                nasa.cmr_granules, "cmr_vj246a1.json"
            ),
            (
                "GET",
                "https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/5200/VJ146A1/fixture.h5",
            ): _json_response("lads-vj146", "lads_vj146a1.json"),
            (
                "GET",
                "https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/5200/VJ246A1/fixture.h5",
            ): _json_response("lads-vj246", "lads_vj246a1.json"),
        }
    )


def sentinel_recorded_transport(*, with_oauth: bool = False) -> RecordedTransport:
    cdse = CopernicusEndpoints()
    item = "https://stac.dataspace.copernicus.eu/v1/collections/sentinel-2-l2a/items/FIXTURE-S2L2A-0001"
    recordings = {
        ("POST", cdse.stac_search + "|collections=sentinel-2-l2a"): _json_response(
            cdse.stac_search, "stac_search_s2l2a.json"
        ),
        ("GET", item): _json_response(item, "stac_item_s2l2a.json"),
    }
    if with_oauth:
        recordings[("POST", cdse.oauth_token)] = _json_response(cdse.oauth_token, "cdse_oauth.json")
    return RecordedTransport(recordings)
