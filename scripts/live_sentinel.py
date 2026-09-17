"""Llamada real a STAC CDSE. No forma parte de pytest. OAuth opcional."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from datahub.adapter import DiscoverCriteria  # noqa: E402
from datahub.adapters.copernicus_sentinel import CopernicusSentinelAdapter  # noqa: E402
from datahub.http import LiveHttpTransport  # noqa: E402


def main() -> int:
    adapter = CopernicusSentinelAdapter(LiveHttpTransport())
    refs = list(adapter.discover(DiscoverCriteria(max_items=2)))
    print(f"discover: {len(refs)} items sentinel-2-l2a")
    for ref in refs:
        print(ref.granule_id, ref.uri)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
