from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .runner import run_pipeline

PHASES = ("ingest", "normalize", "publish", "validate", "all")
SOURCES = ("pokeapi", "opgg", "munchstats")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="champions-dataset",
        description="Scaffold runner for the Pokémon Champions dataset pipeline.",
    )
    parser.add_argument("--phase", choices=PHASES, default="all")
    parser.add_argument(
        "--source",
        dest="sources",
        action="append",
        choices=SOURCES,
        help="Limit scaffold output to one or more source adapters.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        help="Override the default data output root.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned manifest without writing generated files.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = run_pipeline(
        phase=args.phase,
        selected_sources=args.sources,
        output_root=args.output_root,
        dry_run=args.dry_run,
    )
    print(json.dumps(manifest.to_dict(), indent=2))
    return 0
