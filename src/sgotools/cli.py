"""Command line entry point: ``sgotools download`` and ``sgotools summary``."""

from __future__ import annotations

import argparse
import sys

from .constants import CATEGORIES, REGIMES
from .incidents import load_incidents
from .snapshot import Snapshot, download_snapshot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sgotools",
        description="Reproducible access to NHTSA Standing General Order crash data.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    download = sub.add_parser("download", help="fetch a dated snapshot with checksums")
    download.add_argument("dest", help="directory to create")
    download.add_argument("--regime", choices=[*REGIMES, "both"], default="both")
    download.add_argument("--no-definitions", action="store_true")

    summary = sub.add_parser("summary", help="report what a snapshot contains")
    summary.add_argument("path", help="snapshot directory")
    summary.add_argument("--regime", choices=[*REGIMES, "both"], default="both")
    summary.add_argument("--categories", nargs="+", default=["ADS", "ADAS"],
                         choices=list(CATEGORIES))

    args = parser.parse_args(argv)

    if args.command == "download":
        regimes = REGIMES if args.regime == "both" else (args.regime,)
        snapshot = download_snapshot(
            args.dest, regimes=regimes, include_definitions=not args.no_definitions
        )
        manifest = snapshot.manifest or {"files": []}
        ok = sum(1 for f in manifest["files"] if f.get("status") == "ok")
        print(f"{ok}/{len(manifest['files'])} files retrieved into {snapshot.path}")
        return 0 if ok == len(manifest["files"]) else 1

    frame = load_incidents(
        Snapshot(args.path), regime=args.regime, categories=args.categories
    )
    print(frame.attrs["provenance"].summary())
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
