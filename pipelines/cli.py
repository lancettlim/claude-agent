"""CLI entry point for the pipelines package.

Subcommands:
    extract <source>   Run one source extractor (pokeapi | opgg | munchstats)
    validate           Reshape dbt's test results into a validation report
    release            Publish a versioned release package (gated on validate)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from pipelines.extract import munchstats, opgg, pokeapi
from pipelines.release import build as release_build
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
    # dbt build exits non-zero when a data test fails, which is an expected
    # outcome here (a release gate catching bad data) rather than a crash;
    # the report generated below is what surfaces that failure to the caller.
    subprocess.run(["dbt", "build"], cwd=DBT_PROJECT_DIR)
    generated = report.generate()
    failing = [f for f in generated["release_blocking_findings"]]
    if failing:
        print(f"Validation gates failing: {failing}", file=sys.stderr)
        return 1
    print(f"Validation report written to {report.REPORT_PATH}")
    return 0


def _run_release(dataset_version: str, known_limitations: list[str]) -> int:
    try:
        manifest = release_build.build(dataset_version, known_limitations=known_limitations)
    except release_build.ReleaseBlockedError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Published dataset_version {dataset_version}: {len(manifest['tables'])} tables")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pokemon-champions-cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_parser = subparsers.add_parser("extract", help="Run one source extractor")
    extract_parser.add_argument("source", choices=sorted(_EXTRACTORS))

    subparsers.add_parser("validate", help="Run dbt build and write the validation report")

    release_parser = subparsers.add_parser(
        "release", help="Publish a versioned release package (gated on validate)"
    )
    release_parser.add_argument("--version", required=True, dest="dataset_version")
    release_parser.add_argument(
        "--known-limitation",
        action="append",
        dest="known_limitations",
        default=[],
        help="Repeatable; recorded in the manifest and changelog",
    )

    args = parser.parse_args(argv)

    if args.command == "extract":
        return _run_extract(args.source)
    if args.command == "validate":
        return _run_validate()
    if args.command == "release":
        return _run_release(args.dataset_version, args.known_limitations)
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
