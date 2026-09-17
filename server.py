"""Servidor web del visor satelital ECOAVES OrbitalOS.

  pip install ".[server]"
  python3 server.py

Abre http://localhost:8000
"""

from __future__ import annotations

import os
import re
from datetime import date as date_cls
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from datahub.http import LiveHttpTransport
from datahub.imagery import (
    fetch_snapshot,
    geocode,
    list_layers,
    search_sentinel,
)

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"

app = FastAPI(
    title="ECOAVES OrbitalOS Visor",
    description="Visor satelital con NASA Worldview y Copernicus Sentinel-2",
    version="0.1.0",
)


def _transport():
    return LiveHttpTransport(timeout_s=90)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": "ecoaves-orbitalos"}


@app.get("/api/layers")
def api_layers() -> list[dict[str, str]]:
    return list_layers()


@app.get("/api/search")
def api_search(q: str = Query(..., min_length=1, description="Lugar o lat,lon")) -> dict[str, Any]:
    try:
        lat, lon, display_name = geocode(_transport(), q)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"geocoding falló: {exc}") from exc
    return {"lat": lat, "lon": lon, "display_name": display_name}


@app.get("/api/imagery")
def api_imagery(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    date: str | None = Query(None, description="YYYY-MM-DD"),
    layer: str = Query("VIIRS_SNPP_CorrectedReflectance_TrueColor"),
    width: int = Query(1024, ge=64, le=2048),
    height: int = Query(1024, ge=64, le=2048),
) -> Response:
    date_str = date or date_cls.today().isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_str):
        raise HTTPException(status_code=400, detail="date debe ser YYYY-MM-DD")
    try:
        jpeg = fetch_snapshot(
            _transport(),
            lat,
            lon,
            date_str=date_str,
            layer=layer,
            width=width,
            height=height,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"imagery falló: {exc}") from exc
    return Response(content=jpeg, media_type="image/jpeg")


@app.get("/api/sentinel")
def api_sentinel(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    days: int = Query(7, ge=1, le=30),
) -> dict[str, Any]:
    try:
        items = search_sentinel(_transport(), lat, lon, days_back=days)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"sentinel search falló: {exc}") from exc
    return {"lat": lat, "lon": lon, "days": days, "products": items}


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="static/index.html ausente")
    return HTMLResponse(index_file.read_text(encoding="utf-8"))


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def create_app() -> FastAPI:
    """Factory para tests."""
    return app


def main() -> None:
    import uvicorn

    host = os.environ.get("ECOAVES_HOST", "0.0.0.0")
    port = int(os.environ.get("ECOAVES_PORT", "8000"))
    uvicorn.run("server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
