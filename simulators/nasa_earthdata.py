"""Fixtures NASA Black Marble (VIIRS DNB).

Productos confirmados en LAADS DAAC / Earthdata:
- VJ146A1 NOAA-20/JPSS-1 daily TOA nighttime radiance, Level-3, HDF-EOS5
- VJ246A1 NOAA-21/JPSS-2 daily (LAADS page exists; Earthdata still says VJ246 in development)
- VNP46A1 Suomi NPP — deprioritizado: NASA deja de entregar SNPP el 2026-11-01

Tile h08v05: aparece en el ejemplo de nombre de archivo del Black Marble User Guide
Collection 2.0. Esta fixture NO afirma que esa tile cubra Antofagasta ni ningún AOI chileno.

No se inventan concept-id de CMR ni arrays SDS de radiancia.
"""

from __future__ import annotations

from typing import Any

from simulators.licenses import (
    NASA_VJ146A1_LICENSE,
    NASA_VJ246A1_LICENSE,
    NASA_VNP46A1_LICENSE,
)

# Convención oficial: VJ146A1.AYYYYDDD.hXXvYY.CCC.YYYYDDDHHMMSS.h5
VJ146A1_FILENAME = "VJ146A1.A2026001.h08v05.002.2026003120000.h5"
VJ246A1_FILENAME = "VJ246A1.A2026001.h08v05.002.2026003120000.h5"
VNP46A1_FILENAME = "VNP46A1.A2026001.h08v05.002.2026003120000.h5"


def _granule(
    *,
    short_name: str,
    filename: str,
    platform: str,
    license_text: str,
    preferred: bool,
    sunset: str | None = None,
) -> dict[str, Any]:
    body = {
        "synthetic": True,
        "short_name": short_name,
        "producer_granule_id": filename,
        "platform": platform,
        "instrument": "VIIRS",
        "processing_level": "Level-3",
        "collection": "2.0",
        "archive_set": 5200,
        "data_format": "HDF-EOS5",
        "temporal_resolution": "Daily",
        "spatial_resolution": "15 arc-second linear lat/lon grid",
        "tile_id": "h08v05",
        "tile_id_source": (
            "filename example in Black Marble User Guide Collection 2.0 "
            "(VNP46A1.A2018001.h08v05.002....h5); not an Antofagasta AOI claim"
        ),
        "cmr_concept_id": None,
        "cmr_concept_id_note": "CMR concept-id is assigned by NASA; fixture does not invent one",
        "sds": "metadata_only",
        "sds_note": (
            "No radiance arrays in this fixture. VJ146A1/VNP46A1 contain at-sensor DNB "
            "radiance and geometry/cloud-mask SDS as described by LAADS product pages."
        ),
        "preferred_over_vnp46": preferred,
        "snpp_delivery_ends": sunset,
        "citation": (
            "Román, M.O., et al. (2018). NASA's Black Marble nighttime lights product suite. "
            "Remote Sensing of Environment 210, 113-143. doi:10.1016/j.rse.2018.03.017"
        ),
    }
    return {
        "granule_id": filename,
        "product_id": short_name,
        "uri": f"fixture://nasa_earthdata/{filename}",
        "acquisition_time": "2026-01-01T00:00:00Z",
        "license": license_text,
        "processing_level": "Level-3",
        "media_type": "application/json",
        "body": body,
        "georeferenced": True,
        "warning": (
            "Source product is georeferenced (15 arc-second lat/lon tiles). "
            "Fixture omits tile bbox because it was not confirmed against the geographic grid table."
        ),
    }


def nasa_catalog() -> list[dict[str, Any]]:
    return [
        _granule(
            short_name="VJ146A1",
            filename=VJ146A1_FILENAME,
            platform="JPSS-1/NOAA-20",
            license_text=NASA_VJ146A1_LICENSE,
            preferred=True,
        ),
        _granule(
            short_name="VJ246A1",
            filename=VJ246A1_FILENAME,
            platform="JPSS-2/NOAA-21",
            license_text=NASA_VJ246A1_LICENSE,
            preferred=True,
        ),
        _granule(
            short_name="VNP46A1",
            filename=VNP46A1_FILENAME,
            platform="Suomi NPP",
            license_text=NASA_VNP46A1_LICENSE,
            preferred=False,
            sunset="2026-11-01",
        ),
    ]
