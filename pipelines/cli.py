"""CLI entry point for the pipelines package.

Subcommands:
    extract <source>   Run one source extractor (pokeapi | opgg | munchstats | pokebase | bulbagarden)
    validate           Reshape dbt's test results into a validation report
    release            Publish a versioned release package (gated on validate)
    render-card        Render a team card PNG, from a team_id or an ad-hoc build spec
    build-dashboard    Build the static analytics dashboard site from data/marts/*.csv
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path

from pipelines.dashboard import build as dashboard_build
from pipelines.extract import bulbagarden, munchstats, opgg, pokeapi, pokebase
from pipelines.release import build as release_build
from pipelines.render import team_card
from pipelines.validate import report

REPO_ROOT = Path(__file__).resolve().parents[1]
DBT_PROJECT_DIR = REPO_ROOT / "dbt"
STAGING_DIR = REPO_ROOT / "data" / "staging"

_EXTRACTORS = {
    "pokeapi": (pokeapi, STAGING_DIR / "pokeapi.csv"),
    "opgg": (opgg, STAGING_DIR / "opgg_champions.csv"),
    "munchstats": (munchstats, STAGING_DIR / "munchstats.csv"),
    "pokebase": (pokebase, STAGING_DIR / "pokebase.csv"),
    "bulbagarden": (bulbagarden, STAGING_DIR / "bulbagarden.csv"),
}


def _referenced_move_ability_item_names() -> tuple[set[str], set[str], set[str]]:
    """Read data/staging/munchstats.csv for the distinct move/ability/item
    names real tournament rosters reported, so `extract pokeapi` can scope
    its move/ability/item detail fetches to names that matter to the
    dashboard instead of PokéAPI's full catalog. Reads munchstats.csv
    directly (not the dbt-normalized tournament_team_member table) to avoid
    a circular dependency on `dbt build` running before `extract pokeapi`.
    """
    munchstats_path = STAGING_DIR / "munchstats.csv"
    if not munchstats_path.exists():
        return set(), set(), set()

    moves: set[str] = set()
    abilities: set[str] = set()
    items: set[str] = set()
    with munchstats_path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("ability"):
                abilities.add(row["ability"])
            if row.get("item_name"):
                items.add(row["item_name"])
            if row.get("moves"):
                moves.update(name.strip() for name in row["moves"].split("|") if name.strip())
    return moves, abilities, items


def _run_extract(source: str) -> int:
    module, output_path = _EXTRACTORS[source]
    module.extract(output_path)
    if source == "pokeapi":
        moves, abilities, items = _referenced_move_ability_item_names()
        if not moves and not abilities and not items:
            print(
                "Skipping move/ability/item detail extraction: "
                "run `extract munchstats` first so there are names to scope to.",
                file=sys.stderr,
            )
            return 0
        pokeapi.extract_moves(STAGING_DIR / "pokeapi_move.csv", sorted(moves))
        pokeapi.extract_abilities(STAGING_DIR / "pokeapi_ability.csv", sorted(abilities))
        pokeapi.extract_items(STAGING_DIR / "pokeapi_item.csv", sorted(items))
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


def _run_render_card(team_id: str | None, spec_path: Path | None, output_path: Path) -> int:
    if team_id is not None:
        team_card.render_for_team(team_id, output_path)
    else:
        team_card.render_for_spec(spec_path, output_path)
    print(f"Rendered card to {output_path}")
    return 0


def _run_build_dashboard(
    marts_dir: Path | None,
    normalized_dir: Path | None,
    output_dir: Path | None,
    fetch_icons: bool,
) -> int:
    kwargs = {"fetch_icons": fetch_icons}
    if marts_dir is not None:
        kwargs["marts_dir"] = marts_dir
    if normalized_dir is not None:
        kwargs["normalized_dir"] = normalized_dir
    if output_dir is not None:
        kwargs["output_dir"] = output_dir
    payload = dashboard_build.build(**kwargs)
    print(f"Dashboard built with {len(payload['marts'])} mart tables")
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

    render_parser = subparsers.add_parser(
        "render-card", help="Render a team card PNG, from a team_id or an ad-hoc build spec"
    )
    render_source = render_parser.add_mutually_exclusive_group(required=True)
    render_source.add_argument("--team-id", dest="team_id")
    render_source.add_argument("--spec", dest="spec_path", type=Path)
    render_parser.add_argument("--output", required=True, dest="output_path", type=Path)

    dashboard_parser = subparsers.add_parser(
        "build-dashboard", help="Build the static analytics dashboard site from data/marts/*.csv"
    )
    dashboard_parser.add_argument("--marts-dir", dest="marts_dir", type=Path, default=None)
    dashboard_parser.add_argument(
        "--normalized-dir", dest="normalized_dir", type=Path, default=None
    )
    dashboard_parser.add_argument("--output-dir", dest="output_dir", type=Path, default=None)
    dashboard_parser.add_argument(
        "--no-fetch-icons",
        dest="fetch_icons",
        action="store_false",
        default=True,
        help="Skip fetching item icons over the network (species sprites and "
        "move-type icons are always local, offline copies)",
    )

    args = parser.parse_args(argv)

    if args.command == "extract":
        return _run_extract(args.source)
    if args.command == "validate":
        return _run_validate()
    if args.command == "release":
        return _run_release(args.dataset_version, args.known_limitations)
    if args.command == "render-card":
        return _run_render_card(args.team_id, args.spec_path, args.output_path)
    if args.command == "build-dashboard":
        return _run_build_dashboard(
            args.marts_dir, args.normalized_dir, args.output_dir, args.fetch_icons
        )
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
