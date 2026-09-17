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
from typing import Any, Mapping, Optional

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
    {
        "id": "IMERG_Precipitation_Rate",
        "name": "Precipitación (IMERG)",
        "type": "precipitacion",
    },
]

LAYER_IDS = frozenset(item["id"] for item in AVAILABLE_LAYERS)

# Night-lights layer used by DARKSKY overlay
DARKSKY_LAYER = "VIIRS_SNPP_DayNightBand_At_Sensor_Radiance"
PRECIPITATION_LAYER = "IMERG_Precipitation_Rate"

FIRMS_AREA_BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
FIRMS_PUBLIC_SA_CSV = (
    "https://firms.modaps.eosdis.nasa.gov/data/active_fire/"
    "suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_South_America_24h.csv"
)
FIRMS_MAP_KEY_ENV = "FIRMS_MAP_KEY"

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


def fetch_precipitation(
    transport: HttpTransport,
    lat: float,
    lon: float,
    *,
    date_str: str | None = None,
    width: int = 1024,
    height: int = 1024,
    half_deg: float = 1.0,
) -> bytes:
    """JPEG IMERG Precipitation Rate vía Worldview Snapshot."""
    return fetch_snapshot(
        transport,
        lat,
        lon,
        date_str=date_str,
        layer=PRECIPITATION_LAYER,
        width=width,
        height=height,
        half_deg=half_deg,
    )


def search_fires(
    transport: HttpTransport,
    lat: float,
    lon: float,
    *,
    days: int = 1,
    half_deg: float = 1.0,
    map_key: str | None = None,
) -> dict[str, Any]:
    """Busca focos activos NASA FIRMS en el bbox alrededor de (lat, lon).

    Preferencia:
    1. API Area con FIRMS_MAP_KEY (oficial).
    2. CSV público regional VIIRS South America 24h (sin auth), filtrado por bbox.
    """
    import os

    days = max(1, min(int(days), 5))
    lat_min, lon_min, lat_max, lon_max = bbox_around(lat, lon, half_deg=half_deg)
    key = map_key or os.environ.get(FIRMS_MAP_KEY_ENV) or ""

    if key.strip():
        # FIRMS area: west,south,east,north
        area = f"{lon_min},{lat_min},{lon_max},{lat_max}"
        url = f"{FIRMS_AREA_BASE}/{key.strip()}/VIIRS_SNPP_NRT/{area}/{days}"
        response = transport.request(
            "GET",
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/csv"},
        )
        fires = _parse_firms_csv(response.text(), lat_min, lon_min, lat_max, lon_max)
        return {
            "source": "firms_area_api",
            "product": "VIIRS_SNPP_NRT",
            "bbox": [lon_min, lat_min, lon_max, lat_max],
            "days": days,
            "count": len(fires),
            "fires": fires,
        }

    # Fallback público sin MAP_KEY (archivo regional 24h).
    response = transport.request(
        "GET",
        FIRMS_PUBLIC_SA_CSV,
        headers={"User-Agent": USER_AGENT, "Accept": "text/csv"},
    )
    fires = _parse_firms_csv(response.text(), lat_min, lon_min, lat_max, lon_max)
    return {
        "source": "firms_public_csv",
        "product": "SUOMI_VIIRS_C2_South_America_24h",
        "bbox": [lon_min, lat_min, lon_max, lat_max],
        "days": 1,
        "count": len(fires),
        "fires": fires,
        "note": (
            "Sin FIRMS_MAP_KEY: se usa el CSV público regional 24h. "
            "Para API Area NRT con day_range configurable, define FIRMS_MAP_KEY."
        ),
    }


def darksky_status(lat: float, lon: float, *, date_str: str | None = None) -> dict[str, Any]:
    """Metadatos del módulo DARKSKY (overlay DNB). Sin inventar fotometría."""
    when = date_str or date.today().isoformat()
    lat_min, lon_min, lat_max, lon_max = bbox_around(lat, lon)
    return {
        "module": "darksky",
        "layer": DARKSKY_LAYER,
        "date": when,
        "bbox": [lon_min, lat_min, lon_max, lat_max],
        "level": "n/d",
        "levels": ["normal", "observar", "fiscalizar", "critico"],
        "note": (
            "Overlay = VIIRS Day/Night Band (Worldview). "
            "El nivel cuantitativo (normal→crítico) requiere fotometría Black Marble "
            "o el reporte DARKSKY con lote CubeSat; no se inventa aquí."
        ),
    }


def _parse_firms_csv(
    text: str,
    lat_min: float,
    lon_min: float,
    lat_max: float,
    lon_max: float,
) -> list[dict[str, Any]]:
    """Parsea CSV FIRMS y filtra por bbox."""
    import csv
    import io

    if not text or text.lstrip().startswith("<") or "Invalid MAP_KEY" in text:
        raise RuntimeError(f"FIRMS no devolvió CSV válido: {text[:120]!r}")

    reader = csv.DictReader(io.StringIO(text))
    fires: list[dict[str, Any]] = []
    for row in reader:
        try:
            flat = float(row.get("latitude") or row.get("lat") or "")
            flon = float(row.get("longitude") or row.get("lon") or "")
        except (TypeError, ValueError):
            continue
        if not (lat_min <= flat <= lat_max and lon_min <= flon <= lon_max):
            continue
        brightness = row.get("bright_ti4") or row.get("brightness") or row.get("bright_ti5")
        frp = row.get("frp")
        confidence = row.get("confidence")
        acq_date = row.get("acq_date") or row.get("acq_datetime") or ""
        acq_time = row.get("acq_time") or ""
        date_str = f"{acq_date} {acq_time}".strip()
        fires.append(
            {
                "lat": flat,
                "lon": flon,
                "brightness": _as_float(brightness),
                "frp": _as_float(frp),
                "confidence": confidence,
                "date": date_str,
                "satellite": row.get("satellite"),
                "daynight": row.get("daynight"),
            }
        )
    fires.sort(key=lambda item: item.get("frp") or 0.0, reverse=True)
    return fires


def _as_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _asset_href(assets: Mapping[str, Any], key: str) -> Optional[str]:
    asset = assets.get(key)
    if isinstance(asset, dict):
        href = asset.get("href")
        if isinstance(href, str) and href.strip():
            return href
    return None
