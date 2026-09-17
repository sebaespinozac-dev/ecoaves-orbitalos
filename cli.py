"""CLI offline: drop sintético + grabaciones HTTP + DARKSKY. Sin red."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from core.models import SOURCE_COPERNICUS_SENTINEL, SOURCE_CUBESAT_UA, SOURCE_NASA_EARTHDATA
from runtime import build_orchestrator
from simulators.drop import write_cubesat_drop
from simulators.recorded import nasa_recorded_transport, sentinel_recorded_transport


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="orbitalos")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Ingesta las 3 fuentes (grabaciones) y corre DARKSKY")
    run.add_argument("--drop", required=True)
    run.add_argument("--db", required=True)
    run.add_argument("--batch", required=True)
    run.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if args.command == "run":
        write_cubesat_drop(args.drop, batch_id=args.batch, profile="worsening")
        orch = build_orchestrator(
            db_path=args.db,
            drop_dir=args.drop,
            nasa_transport=nasa_recorded_transport(),
            sentinel_transport=sentinel_recorded_transport(),
        )
        counts = orch.ingest_sources(
            [SOURCE_NASA_EARTHDATA, SOURCE_CUBESAT_UA, SOURCE_COPERNICUS_SENTINEL],
            batch_id=args.batch,
        )
        report = orch.process_app("darksky", batch_id=args.batch)
        if args.out:
            out = Path(args.out)
            out.mkdir(parents=True, exist_ok=True)
            (out / f"{args.batch}.darksky.json").write_text(
                json.dumps(report.payload, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            (out / f"{args.batch}.darksky.txt").write_text(report.summary_text, encoding="utf-8")
        print(json.dumps({"ingest": counts, "sentinel_used": report.payload["sentinel_used"]}, indent=2))
        print(report.summary_text)
        orch.storage.close()
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
