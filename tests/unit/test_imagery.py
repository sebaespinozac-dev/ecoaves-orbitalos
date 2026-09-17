"""Tests unitarios para datahub.imagery — sin red."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from datahub.http import HttpResponse, RecordedTransport, UnexpectedHttpError
from datahub.imagery import (
    AVAILABLE_LAYERS,
    COPERNICUS_STAC_SEARCH,
    NOMINATIM_SEARCH,
    WORLDVIEW_SNAPSHOT,
    bbox_around,
    fetch_snapshot,
    geocode,
    list_layers,
    parse_location_query,
    search_sentinel,
)

RECORDINGS = Path(__file__).resolve().parents[1] / "integration" / "recordings"


def _imagery_transport() -> RecordedTransport:
    jpeg = (RECORDINGS / "worldview_snapshot.jpg").read_bytes()
    stac = (RECORDINGS / "stac_search_antofagasta.json").read_bytes()
    nominatim = (RECORDINGS / "nominatim_antofagasta.json").read_bytes()

    # Match any Worldview snapshot GET (params vary by date/bbox)
    class FlexibleTransport:
        def request(self, method, url, *, headers=None, params=None, json_body=None, form=None):
            method = method.upper()
            if method == "GET" and url.startswith(WORLDVIEW_SNAPSHOT):
                return HttpResponse(
                    status=200,
                    url=url,
                    headers={"content-type": "image/jpeg"},
                    body=jpeg,
                )
            if method == "POST" and url == COPERNICUS_STAC_SEARCH:
                return HttpResponse(
                    status=200,
                    url=url,
                    headers={"content-type": "application/geo+json"},
                    body=stac,
                )
            if method == "GET" and url.startswith(NOMINATIM_SEARCH):
                return HttpResponse(
                    status=200,
                    url=url,
                    headers={"content-type": "application/json"},
                    body=nominatim,
                )
            raise UnexpectedHttpError(f"no grabación para {method} {url}")

    return FlexibleTransport()  # type: ignore[return-value]


def test_bbox_around_point() -> None:
    lat_min, lon_min, lat_max, lon_max = bbox_around(-23.6509, -70.3975)
    assert lat_min == pytest.approx(-24.6509)
    assert lon_min == pytest.approx(-71.3975)
    assert lat_max == pytest.approx(-22.6509)
    assert lon_max == pytest.approx(-69.3975)


def test_parse_location_query_coords() -> None:
    assert parse_location_query("-23.6509, -70.3975") == (-23.6509, -70.3975)
    assert parse_location_query(" -23.6509;-70.3975 ") == (-23.6509, -70.3975)
    assert parse_location_query("Antofagasta") is None


def test_list_layers_has_viirs_and_modis() -> None:
    layers = list_layers()
    ids = {item["id"] for item in layers}
    assert "VIIRS_SNPP_CorrectedReflectance_TrueColor" in ids
    assert "VIIRS_SNPP_DayNightBand_At_Sensor_Radiance" in ids
    assert "MODIS_Terra_CorrectedReflectance_TrueColor" in ids
    assert layers == AVAILABLE_LAYERS or len(layers) == len(AVAILABLE_LAYERS)


def test_fetch_snapshot_returns_jpeg() -> None:
    body = fetch_snapshot(
        _imagery_transport(),
        -23.6509,
        -70.3975,
        date_str="2026-09-10",
    )
    assert body[:2] == b"\xff\xd8"
    assert len(body) > 10


def test_fetch_snapshot_rejects_unknown_layer() -> None:
    with pytest.raises(ValueError, match="capa no soportada"):
        fetch_snapshot(_imagery_transport(), -23.0, -70.0, layer="NOT_A_LAYER")


def test_search_sentinel_returns_products() -> None:
    items = search_sentinel(_imagery_transport(), -23.6509, -70.3975, days_back=7)
    assert len(items) == 2
    assert items[0]["cloud_cover"] == 12.4
    assert items[0]["thumbnail_url"].startswith("https://")
    assert items[1]["datetime"].startswith("2026-09-08")


def test_geocode_place_name() -> None:
    lat, lon, name = geocode(_imagery_transport(), "Antofagasta")
    assert lat == pytest.approx(-23.6509)
    assert lon == pytest.approx(-70.3975)
    assert "Antofagasta" in name


def test_geocode_coordinate_string() -> None:
    lat, lon, name = geocode(_imagery_transport(), "-23.6509, -70.3975")
    assert lat == pytest.approx(-23.6509)
    assert lon == pytest.approx(-70.3975)
    assert "23.6509" in name
