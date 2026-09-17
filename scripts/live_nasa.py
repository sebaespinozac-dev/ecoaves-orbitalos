"""Llamada real a CMR. No forma parte de pytest. Requiere EARTHDATA_TOKEN."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from datahub.adapter import DiscoverCriteria  # noqa: E402
from datahub.adapters.nasa_earthdata import EARTHDATA_TOKEN_ENV, NasaEarthdataAdapter  # noqa: E402
from datahub.http import LiveHttpTransport  # noqa: E402


def main() -> int:
    if not os.environ.get(EARTHDATA_TOKEN_ENV):
        print(f"Falta {EARTHDATA_TOKEN_ENV}. Ver datahub/adapters/nasa_earthdata/README.md", file=sys.stderr)
        return 2
    adapter = NasaEarthdataAdapter(LiveHttpTransport())
    refs = list(adapter.discover(DiscoverCriteria(max_items=3)))
    print(f"discover: {len(refs)} gránulos")
    for ref in refs:
        print(ref.product_id, ref.granule_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
