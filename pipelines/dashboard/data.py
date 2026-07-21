"""Loads data/marts/*.csv into the JSON payload the dashboard template
bakes into its generated HTML.

Uses plain csv.DictReader (no pandas/dbt runtime), matching the rest of
this codebase's convention of not requiring a build runtime just to read
already-materialized output (see pipelines/render/data_source.py). Missing
mart files degrade to an empty list rather than raising, so the dashboard
still builds (with empty-state sections) before `make dbt-build` has ever
been run.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MARTS_DIR = REPO_ROOT / "data" / "marts"
DEFAULT_NORMALIZED_DIR = REPO_ROOT / "data" / "normalized"

# mart_name -> (int_fields, float_fields) for numeric coercion; every other
# column is left as a string.
MART_FIELDS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "pokemon_usage_summary": (("usage_count", "usage_rank"), ()),
    "legality_summary_by_regulation": (("legal_pokemon_count",), ()),
    "stat_change_leaderboard": (("stat_total_delta", "rank_within_direction"), ()),
    "pokemon_win_rate_summary": (
        ("total_wins", "total_losses", "record_count"),
        ("win_rate",),
    ),
    "pokemon_build_usage": (("usage_count", "usage_rank"), ()),
    "pokemon_move_usage": (("usage_count", "usage_rank"), ()),
}


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _coerce(
    row: dict[str, str], *, int_fields: tuple[str, ...], float_fields: tuple[str, ...]
) -> dict[str, Any]:
    coerced: dict[str, Any] = dict(row)
    for field in int_fields:
        value = coerced.get(field)
        coerced[field] = int(value) if value not in (None, "") else None
    for field in float_fields:
        value = coerced.get(field)
        coerced[field] = float(value) if value not in (None, "") else None
    return coerced


def load_mart(marts_dir: Path, mart_name: str) -> list[dict[str, Any]]:
    """Returns [] (not an error) if the mart's CSV doesn't exist yet."""
    int_fields, float_fields = MART_FIELDS[mart_name]
    rows = _read_csv_rows(marts_dir / f"{mart_name}.csv")
    return [_coerce(row, int_fields=int_fields, float_fields=float_fields) for row in rows]


def load_pokemon_names(normalized_dir: Path = DEFAULT_NORMALIZED_DIR) -> dict[str, str]:
    """pokemon_key -> pokemon_name, for friendlier labels than raw keys.
    Returns {} gracefully if data/normalized/pokemon.csv isn't present."""
    return {
        row["pokemon_key"]: row["pokemon_name"]
        for row in _read_csv_rows(normalized_dir / "pokemon.csv")
    }


def load_marts(marts_dir: Path = DEFAULT_MARTS_DIR) -> dict[str, list[dict[str, Any]]]:
    return {mart_name: load_mart(marts_dir, mart_name) for mart_name in MART_FIELDS}


def _join_pokemon_names(
    marts: dict[str, list[dict[str, Any]]], pokemon_names: dict[str, str]
) -> dict[str, list[dict[str, Any]]]:
    joined = {}
    for mart_name, rows in marts.items():
        joined[mart_name] = [
            {**row, "pokemon_name": pokemon_names.get(row["pokemon_key"], row["pokemon_key"])}
            if "pokemon_key" in row
            else row
            for row in rows
        ]
    return joined


def compute_kpis(marts: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    usage_rows = [r for r in marts["pokemon_usage_summary"] if not r.get("event_tier")]
    legality_rows = marts["legality_summary_by_regulation"]
    win_rate_rows = marts["pokemon_win_rate_summary"]
    stat_rows = marts["stat_change_leaderboard"]

    latest_snapshot_date = max((r["snapshot_date"] for r in legality_rows), default=None)
    legal_pool_by_regulation = [
        {"regulation_code": r["regulation_code"], "legal_pokemon_count": r["legal_pokemon_count"]}
        for r in legality_rows
        if r["snapshot_date"] == latest_snapshot_date
    ]

    top_used = min(usage_rows, key=lambda r: r["usage_rank"], default=None)

    # Prefer a win-rate leader with a reasonable sample size, so a 1-0
    # record doesn't outrank a well-established Pokémon.
    RECORD_COUNT_FLOOR = 5
    qualified_win_rates = [r for r in win_rate_rows if r["record_count"] >= RECORD_COUNT_FLOOR]
    top_win_rate_pool = qualified_win_rates or win_rate_rows
    top_win_rate = max(top_win_rate_pool, key=lambda r: r["win_rate"], default=None)

    return {
        "latest_snapshot_date": latest_snapshot_date,
        "legal_pool_by_regulation": legal_pool_by_regulation,
        "distinct_pokemon_used": len(usage_rows),
        "top_used_pokemon": top_used,
        "top_win_rate_pokemon": top_win_rate,
        "stat_changes_tracked": sum(1 for r in stat_rows if r["stat_total_delta"] != 0),
    }


def compute_flags(marts: dict[str, list[dict[str, Any]]]) -> dict[str, bool]:
    stat_rows = marts["stat_change_leaderboard"]
    legality_rows = marts["legality_summary_by_regulation"]

    stat_changes_degenerate = not any(r["stat_total_delta"] != 0 for r in stat_rows)
    distinct_dates = {r["snapshot_date"] for r in legality_rows}
    trend_degenerate = len(distinct_dates) <= 1

    return {
        "stat_changes_degenerate": stat_changes_degenerate,
        "trend_degenerate": trend_degenerate,
    }


def build_payload(
    marts_dir: Path = DEFAULT_MARTS_DIR, normalized_dir: Path = DEFAULT_NORMALIZED_DIR
) -> dict[str, Any]:
    marts = load_marts(marts_dir)
    pokemon_names = load_pokemon_names(normalized_dir)
    marts = _join_pokemon_names(marts, pokemon_names)
    return {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "kpis": compute_kpis(marts),
        "flags": compute_flags(marts),
        "marts": marts,
    }
