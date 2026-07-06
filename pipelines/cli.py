"""CLI entry point for the pipelines package.

Subcommands:
    extract <source>   Run one source extractor (pokeapi | opgg | munchstats)
    validate           Reshape dbt's test results into a validation report
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from pipelines.extract import munchstats, opgg, pokeapi
from pipelines.validate import report

REPO_ROOT = Path(__file__).resolve().parents[1]
DBT_PROJECT_DIR = REPO_ROOT / "dbt"

_EXTRACTORS = {
    "pokeapi": (pokeapi, REPO_ROOT / "data" / "staging" / "pokeapi.csv"),
    "opgg": (opgg, REPO_ROOT / "data" / "staging" / "opgg_champions.csv"),
    "munchstats": (munchstats, REPO_ROOT / "data" / "staging" / "munchstats.csv"),
}


def _run_extract(source: str) -> int:
    module, output_path = _EXTRACTORS[source]
    module.extract(output_path)
    return 0


def _run_validate() -> int:
    subprocess.run(["dbt", "build"], cwd=DBT_PROJECT_DIR, check=True)
    generated = report.generate()
    failing = [f for f in generated["release_blocking_findings"]]
    if failing:
        print(f"Validation gates failing: {failing}", file=sys.stderr)
        return 1
    print(f"Validation report written to {report.REPORT_PATH}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pokemon-champions-cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_parser = subparsers.add_parser("extract", help="Run one source extractor")
    extract_parser.add_argument("source", choices=sorted(_EXTRACTORS))

    subparsers.add_parser("validate", help="Run dbt build and write the validation report")

    args = parser.parse_args(argv)

    if args.command == "extract":
        return _run_extract(args.source)
    if args.command == "validate":
        return _run_validate()
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
