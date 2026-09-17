"""Tests de endpoints del visor — transporte mockeado, sin red."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import server
from datahub.http import HttpResponse, UnexpectedHttpError
from datahub.imagery import (
    COPERNICUS_STAC_SEARCH,
    NOMINATIM_SEARCH,
    WORLDVIEW_SNAPSHOT,
)

RECORDINGS = Path(__file__).resolve().parents[1] / "integration" / "recordings"


class _MockTransport:
    def request(self, method, url, *, headers=None, params=None, json_body=None, form=None):
        method = method.upper()
        if method == "GET" and url.startswith(WORLDVIEW_SNAPSHOT):
            return HttpResponse(
                status=200,
                url=url,
                headers={"content-type": "image/jpeg"},
                body=(RECORDINGS / "worldview_snapshot.jpg").read_bytes(),
            )
        if method == "POST" and url == COPERNICUS_STAC_SEARCH:
            return HttpResponse(
                status=200,
                url=url,
                headers={"content-type": "application/geo+json"},
                body=(RECORDINGS / "stac_search_antofagasta.json").read_bytes(),
            )
        if method == "GET" and url.startswith(NOMINATIM_SEARCH):
            return HttpResponse(
                status=200,
                url=url,
                headers={"content-type": "application/json"},
                body=(RECORDINGS / "nominatim_antofagasta.json").read_bytes(),
            )
        raise UnexpectedHttpError(f"no grabación para {method} {url}")


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(server, "_transport", lambda: _MockTransport())
    return TestClient(server.app)


def test_health(client: TestClient) -> None:
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_layers(client: TestClient) -> None:
    res = client.get("/api/layers")
    assert res.status_code == 200
    ids = {item["id"] for item in res.json()}
    assert "VIIRS_SNPP_CorrectedReflectance_TrueColor" in ids


def test_search_place(client: TestClient) -> None:
    res = client.get("/api/search", params={"q": "Antofagasta"})
    assert res.status_code == 200
    data = res.json()
    assert data["lat"] == pytest.approx(-23.6509)
    assert "Antofagasta" in data["display_name"]


def test_search_coords(client: TestClient) -> None:
    res = client.get("/api/search", params={"q": "-23.6509, -70.3975"})
    assert res.status_code == 200
    data = res.json()
    assert data["lon"] == pytest.approx(-70.3975)


def test_imagery_returns_jpeg(client: TestClient) -> None:
    res = client.get(
        "/api/imagery",
        params={
            "lat": -23.6509,
            "lon": -70.3975,
            "date": "2026-09-10",
            "layer": "VIIRS_SNPP_CorrectedReflectance_TrueColor",
        },
    )
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("image/jpeg")
    assert res.content[:2] == b"\xff\xd8"


def test_imagery_bad_layer(client: TestClient) -> None:
    res = client.get(
        "/api/imagery",
        params={"lat": -23.0, "lon": -70.0, "layer": "NOPE"},
    )
    assert res.status_code == 400


def test_sentinel(client: TestClient) -> None:
    res = client.get("/api/sentinel", params={"lat": -23.6509, "lon": -70.3975, "days": 7})
    assert res.status_code == 200
    products = res.json()["products"]
    assert len(products) == 2
    assert products[0]["thumbnail_url"]


def test_index_serves_html(client: TestClient) -> None:
    res = client.get("/")
    assert res.status_code == 200
    assert "ECOAVES OrbitalOS" in res.text
    assert "leaflet" in res.text.lower()
