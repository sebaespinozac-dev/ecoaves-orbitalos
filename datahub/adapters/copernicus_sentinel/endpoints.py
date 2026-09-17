"""URLs CDSE / Sentinel Hub aisladas. Rutas SH se reestructuraron en marzo 2026: no hardcodear en Core."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_STAC_SEARCH = "https://stac.dataspace.copernicus.eu/v1/search"
DEFAULT_OAUTH_TOKEN = (
    "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
)
DEFAULT_SH_PROCESS = "https://sh.dataspace.copernicus.eu/api/v1/process"

CDSE_CLIENT_ID_ENV = "CDSE_CLIENT_ID"
CDSE_CLIENT_SECRET_ENV = "CDSE_CLIENT_SECRET"


@dataclass(frozen=True)
class CopernicusEndpoints:
    stac_search: str = DEFAULT_STAC_SEARCH
    oauth_token: str = DEFAULT_OAUTH_TOKEN
    sentinel_hub_process: str = DEFAULT_SH_PROCESS

    @classmethod
    def from_environ(cls, env: dict[str, str] | None = None) -> "CopernicusEndpoints":
        env = env or dict(os.environ)
        return cls(
            stac_search=env.get("ECOAVES_CDSE_STAC_SEARCH", DEFAULT_STAC_SEARCH),
            oauth_token=env.get("ECOAVES_CDSE_OAUTH_TOKEN", DEFAULT_OAUTH_TOKEN),
            sentinel_hub_process=env.get("ECOAVES_CDSE_SH_PROCESS", DEFAULT_SH_PROCESS),
        )
