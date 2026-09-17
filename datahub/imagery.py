"""Obtención de imágenes satelitales y geocoding para el visor.

Fuentes públicas (sin API key para el MVP):
- NASA Worldview Snapshot API → JPEG true-color / night lights
- Copernicus STAC search → metadatos + thumbnails Sentinel-2
- OpenStreetMap Nominatim → geocoding

Todas las llamadas HTTP pasan por un HttpTransport inyectable.
CI usa grabaciones; live usa LiveHttpTransport.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Mapping, Optional, Sequence
from urllib.parse import quote

from datahub.http import HttpTransport

WORLDVIEW_SNAPSHOT = "https://wvs.earthdata.nasa.gov/api/v1/snapshot"
COPERNICUS_STAC_SEARCH = "https://catalogue.dataspace.copernicus.eu/stac/search"
NOMINATIM_SEARCH = "https://nominatim.openstreetmap.org/search"

USER_AGENT = "ECOAVES-OrbitalOS/1.0 (ground viewer; contact: ecoaves)"

AVAILABLE_LAYERS: list[dict[str, str]] = [
    {
        "id": "VIIRS_SNPP_CorrectedReflectance_TrueColor",
        "name": "Color verdadero (VIIRS)",
        "type": "diurno",
    },
    {
        "id": "VIIRS_SNPP_DayNightBand_At_Sensor_Radiance",
        "name": "Luces nocturnas (VIIRS)",
        "type": "nocturno",
    },
    {
        "id": "MODIS_Terra_CorrectedReflectance_TrueColor",
        "name": "Color verdadero (MODIS)",
        "type": "diurno",
    },
]

LAYER_IDS = frozenset(item["id"] for item in AVAILABLE_LAYERS)

_COORD_RE = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?)\s*[,;\s]\s*(-?\d+(?:\.\d+)?)\s*$"
)


def bbox_around(lat: float, lon: float, *, half_deg: float = 1.0) -> tuple[float, float, float, float]:
    """Retorna (lat_min, lon_min, lat_max, lon_max) con ±half_deg."""
    lat_min = max(-90.0, lat - half_deg)
    lat_max = min(90.0, lat + half_deg)
    lon_min = max(-180.0, lon - half_deg)
    lon_max = min(180.0, lon + half_deg)
    return (lat_min, lon_min, lat_max, lon_max)


def parse_location_query(query: str) -> tuple[float, float] | None:
    """Si el texto es 'lat, lon', retorna (lat, lon). Si no, None."""
    match = _COORD_RE.match(query.strip())
    if not match:
        return None
    a, b = float(match.group(1)), float(match.group(2))
    # Heurística: lat en [-90,90], lon en [-180,180]
    if abs(a) <= 90 and abs(b) <= 180:
        return a, b
    if abs(b) <= 90 and abs(a) <= 180:
        return b, a
    return None


def fetch_snapshot(
    transport: HttpTransport,
    lat: float,
    lon: float,
    *,
    date_str: str | None = None,
    layer: str = "VIIRS_SNPP_CorrectedReflectance_TrueColor",
    width: int = 1024,
    height: int = 1024,
    half_deg: float = 1.0,
) -> bytes:
    """Descarga un JPEG de NASA Worldview Snapshot alrededor de (lat, lon)."""
    if layer not in LAYER_IDS:
        raise ValueError(f"capa no soportada: {layer!r}; admitidas: {sorted(LAYER_IDS)}")
    when = date_str or date.today().isoformat()
    lat_min, lon_min, lat_max, lon_max = bbox_around(lat, lon, half_deg=half_deg)
    # Worldview BBOX order: lat_min,lon_min,lat_max,lon_max
    bbox = f"{lat_min},{lon_min},{lat_max},{lon_max}"
    params = {
        "REQUEST": "GetSnapshot",
        "LAYERS": layer,
        "CRS": "EPSG:4326",
        "TIME": when,
        "WRAP": "DAY",
        "BBOX": bbox,
        "FORMAT": "image/jpeg",
        "WIDTH": str(width),
        "HEIGHT": str(height),
    }
    response = transport.request(
        "GET",
        WORLDVIEW_SNAPSHOT,
        headers={"User-Agent": USER_AGENT, "Accept": "image/jpeg"},
        params=params,
    )
    if response.status >= 400:
        raise RuntimeError(f"Worldview snapshot HTTP {response.status}")
    body = response.body
    if not body or body[:2] not in (b"\xff\xd8", b"\x89P"):  # JPEG o PNG
        # Algunas respuestas de error son XML/text
        preview = body[:120].decode("utf-8", errors="replace")
        raise RuntimeError(f"Worldview no devolvió imagen: {preview!r}")
    return body


def search_sentinel(
    transport: HttpTransport,
    lat: float,
    lon: float,
    *,
    days_back: int = 7,
    limit: int = 10,
    half_deg: float = 1.0,
) -> list[dict[str, Any]]:
    """Busca productos Sentinel-2 L2A recientes (STAC). Thumbnails públicos."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=max(1, days_back))
    lat_min, lon_min, lat_max, lon_max = bbox_around(lat, lon, half_deg=half_deg)
    # STAC bbox: [west, south, east, north]
    body = {
        "collections": ["sentinel-2-l2a"],
        "bbox": [lon_min, lat_min, lon_max, lat_max],
        "datetime": f"{start.strftime('%Y-%m-%dT%H:%M:%SZ')}/{end.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "limit": limit,
        "sortby": [{"field": "datetime", "direction": "desc"}],
    }
    response = transport.request(
        "POST",
        COPERNICUS_STAC_SEARCH,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/geo+json",
            "Content-Type": "application/json",
        },
        json_body=body,
    )
    payload = response.json()
    results: list[dict[str, Any]] = []
    for feature in payload.get("features") or ():
        props = feature.get("properties") or {}
        assets = feature.get("assets") or {}
        thumbnail = _asset_href(assets, "thumbnail") or _asset_href(assets, "overview")
        results.append(
            {
                "id": feature.get("id"),
                "datetime": props.get("datetime"),
                "cloud_cover": props.get("eo:cloud_cover"),
                "thumbnail_url": thumbnail,
                "collection": feature.get("collection") or "sentinel-2-l2a",
                "bbox": feature.get("bbox"),
            }
        )
    return results


def geocode(
    transport: HttpTransport,
    query: str,
) -> tuple[float, float, str]:
    """Geocodifica un lugar con Nominatim. Retorna (lat, lon, display_name)."""
    coords = parse_location_query(query)
    if coords is not None:
        lat, lon = coords
        return lat, lon, f"{lat:.5f}, {lon:.5f}"

    response = transport.request(
        "GET",
        NOMINATIM_SEARCH,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        params={"q": query, "format": "json", "limit": "1"},
    )
    items = response.json()
    if not isinstance(items, list) or not items:
        raise LookupError(f"no se encontró el lugar: {query!r}")
    hit = items[0]
    return float(hit["lat"]), float(hit["lon"]), str(hit.get("display_name") or query)


def list_layers() -> list[dict[str, str]]:
    """Capas Worldview disponibles en el visor."""
    return [dict(item) for item in AVAILABLE_LAYERS]


def _asset_href(assets: Mapping[str, Any], key: str) -> Optional[str]:
    asset = assets.get(key)
    if isinstance(asset, dict):
        href = asset.get("href")
        if isinstance(href, str) and href.strip():
            return href
    return None
