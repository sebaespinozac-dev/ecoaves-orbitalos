"""URLs NASA / CMR / LAADS aisladas del Core. Sobrescribibles por entorno (Earthdata 2026)."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_CMR_GRANULES = "https://cmr.earthdata.nasa.gov/search/granules.umm_json"
DEFAULT_CMR_CLIENT_ID = "ecoaves-orbitalos"


@dataclass(frozen=True)
class NasaEndpoints:
    cmr_granules: str = DEFAULT_CMR_GRANULES
    client_id: str = DEFAULT_CMR_CLIENT_ID

    @classmethod
    def from_environ(cls, env: dict[str, str] | None = None) -> "NasaEndpoints":
        env = env or dict(os.environ)
        return cls(
            cmr_granules=env.get("ECOAVES_CMR_GRANULES", DEFAULT_CMR_GRANULES),
            client_id=env.get("ECOAVES_CMR_CLIENT_ID", DEFAULT_CMR_CLIENT_ID),
        )


# Earthdata Login bearer token. Nunca hardcodear. Nunca commitear.
EARTHDATA_TOKEN_ENV = "EARTHDATA_TOKEN"
