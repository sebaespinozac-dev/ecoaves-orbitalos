"""Fixture Copernicus Sentinel-2 L2A (STAC CDSE).

Colección confirmada: sentinel-2-l2a en https://stac.dataspace.copernicus.eu/v1
(documentación CDSE). Bandas ópticas MSI L2A documentadas por ESA.

No existe producto Sentinel equivalente a luces nocturnas VIIRS / Black Marble.
Esta fixture no finge ese uso. DARKSKY no la consumirá en el MVP (hito 5).

No se inventa un item STAC real ni un tile MGRS chileno.
"""

from __future__ import annotations

from typing import Any

from core.models import COPERNICUS_S2_L2A_COLLECTION
from simulators.licenses import COPERNICUS_SENTINEL_LICENSE

# Bandas ópticas L2A documentadas (ESA Sentinel-2). Lista corta, no exhaustiva.
S2_L2A_BANDS = (
    {"name": "B02", "common_name": "blue", "gsd": 10},
    {"name": "B03", "common_name": "green", "gsd": 10},
    {"name": "B04", "common_name": "red", "gsd": 10},
    {"name": "B08", "common_name": "nir", "gsd": 10},
)

ITEM_ID = "FIXTURE-S2L2A-0001"


def sentinel_catalog() -> list[dict[str, Any]]:
    body = {
        "type": "Feature",
        "stac_version": "1.0.0",
        "id": ITEM_ID,
        "collection": COPERNICUS_S2_L2A_COLLECTION,
        "synthetic": True,
        "properties": {
            "datetime": "2026-01-15T14:32:11Z",
            "platform": "sentinel-2a",
            "instruments": ["msi"],
            "product_type": "S2MSI2A",
            "processing:level": "L2A",
        },
        "geometry": None,
        "bbox": None,
        "assets": {
            band["name"]: {
                "title": band["common_name"],
                "gsd": band["gsd"],
                "href": f"fixture://copernicus_sentinel/{ITEM_ID}/{band['name']}",
                "eo:bands": [band],
            }
            for band in S2_L2A_BANDS
        },
        "night_lights_product": False,
        "note": (
            "Synthetic STAC-shaped fixture for contract tests. Not a CDSE item. "
            "Sentinel-2 L2A is optical surface reflectance, not VIIRS DNB nighttime lights."
        ),
    }
    return [
        {
            "granule_id": ITEM_ID,
            "product_id": COPERNICUS_S2_L2A_COLLECTION,
            "uri": f"fixture://copernicus_sentinel/{ITEM_ID}",
            "acquisition_time": "2026-01-15T14:32:11Z",
            "license": COPERNICUS_SENTINEL_LICENSE,
            "processing_level": "L2A",
            "media_type": "application/geo+json",
            "body": body,
            "georeferenced": True,
            "warning": (
                "Source product is georeferenced. Fixture omits geometry/bbox "
                "because no real STAC item was fetched."
            ),
        }
    ]
