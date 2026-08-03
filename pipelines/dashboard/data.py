"""Loads data/marts/*.csv into the JSON payload the dashboard template
bakes into its generated HTML.

Uses plain csv.DictReader (no pandas/dbt runtime), matching the rest of
this codebase's convention of not requiring a build runtime just to read
already-materialized output (see pipelines/render/data_source.py). Missing
mart files degrade to an empty list rather than raising, so the dashboard
still builds before `make dbt-build` has ever been run. (An earlier version
of this module also computed empty-state flags for two now-removed
sections — stat-change leaderboard and legal-pool trend — that were cut
because the underlying data is permanently degenerate; see
docs/dashboard.md's "Removed sections" note. No empty-state computation
remains here.)
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
    "pokemon_usage_summary": (("usage_count", "usage_rank"), ("usage_share",)),
    "legality_summary_by_regulation": (
        ("legal_pokemon_count", "cumulative_legal_pokemon_count"),
        (),
    ),
    "pokemon_win_rate_summary": (
        ("total_wins", "total_losses", "record_count", "wilson_rank"),
        ("win_rate", "wilson_lower_bound"),
    ),
    "pokemon_item_usage": (("usage_count", "usage_rank"), ("item_share",)),
    "pokemon_ability_usage": (("usage_count", "usage_rank"), ("ability_share",)),
    "pokemon_move_usage": (
        ("usage_count", "usage_rank", "power", "accuracy", "priority", "pp"),
        ("move_share",),
    ),
    "pokemon_team_core_usage": (("co_occurrence_count", "usage_rank"), ("partner_share",)),
    "pokemon_champions_profile": (
        (
            "hp",
            "attack",
            "defense",
            "sp_attack",
            "sp_defense",
            "speed",
            "stat_total",
            "usage_count",
            "record_count",
        ),
        ("usage_share", "win_rate"),
    ),
    "top_tournament_teams": (
        ("record_wins", "record_losses", "placement", "team_rank"),
        ("win_rate",),
    ),
    "pokemon_usage_by_event_date": (("usage_count", "usage_rank"), ("usage_share",)),
    "pokemon_head_to_head": (
        ("matches_played", "wins", "losses", "matchup_rank"),
        ("win_rate", "wilson_lower_bound"),
    ),
    "pokemon_matchup_summary": (
        (
            "distinct_opponents",
            "total_matchup_appearances",
            "best_matchup_matches",
            "worst_matchup_matches",
            "min_matches_threshold",
        ),
        ("overall_win_rate", "best_matchup_win_rate", "worst_matchup_win_rate"),
    ),
    "pokemon_placement_weighted_usage": (
        ("usage_count", "top_cut_usage_count", "weighted_usage_rank"),
        ("top_cut_usage_share", "placement_weighted_score", "weighted_usage_share"),
    ),
    "pokemon_usage_by_regulation": (("usage_count", "usage_rank"), ("usage_share",)),
    "pokemon_build_concentration": (
        ("item_count", "ability_count"),
        ("item_hhi", "ability_hhi"),
    ),
    "pokemon_team_synergy": (("pair_team_count", "lift_rank"), ("lift",)),
    "pokemon_speed_tiers": (
        (
            "base_speed",
            "max_investment_speed",
            "plus_one_speed",
            "scarf_speed",
            "plus_two_speed",
            "tailwind_speed",
            "scarf_tailwind_speed",
            "usage_count",
            "record_count",
        ),
        ("usage_share", "win_rate"),
    ),
    "pokemon_usage_by_country": (
        ("usage_count", "country_usage_rank"),
        ("usage_share",),
    ),
    "player_signature_pokemon": (
        ("player_team_count", "usage_count", "player_pokemon_rank"),
        ("player_usage_share",),
    ),
}

# Two of the marts above are far larger than anything the dashboard can
# display, and the whole payload is inlined into the committed
# docs/dashboard/index.html (see pipelines/dashboard/build.py's docstring)
# — player_signature_pokemon alone is ~44,500 rows, which would roughly
# double that already-7MB committed file for rows no view ever reads.
#
# Each slice below is also the analytically honest cut, not just a size
# cut: both marts' own schema.yml entries warn that their headline metric
# is noise below a sample-size floor (lift is unstable at low
# pair_team_count; a "signature Pokémon" claim from a player with one
# recorded team is weak evidence), and both expose that sample size as a
# column precisely so consumers can apply a floor. The floors are applied
# here rather than in dbt so the marts themselves stay complete for
# docs/local-queries.md's ad-hoc querying.
MIN_SYNERGY_PAIR_TEAMS = 5
MAX_SYNERGY_PARTNERS_PER_POKEMON = 12
# Deliberately 2, not a larger "established player" number: only three
# Champions-format events exist anywhere (see backlog.md #26), so three
# recorded teams is the ceiling, not a modest bar. Measured against the
# real mart, 2,329 players have exactly one recorded team, 358 have two,
# and exactly one has three -- a floor of 3 would leave the whole view
# showing a single player. Two teams is therefore the strongest "this
# wasn't one event's worth of choices" signal the format can produce.
MIN_SIGNATURE_PLAYER_TEAMS = 2
MAX_SIGNATURE_PICKS_PER_PLAYER = 6


def _slice_team_synergy(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    kept = [r for r in rows if (r.get("pair_team_count") or 0) >= MIN_SYNERGY_PAIR_TEAMS]
    per_anchor: dict[str, int] = {}
    out = []
    for row in sorted(kept, key=lambda r: (r["pokemon_key"], -(r.get("lift") or 0))):
        seen = per_anchor.get(row["pokemon_key"], 0)
        if seen >= MAX_SYNERGY_PARTNERS_PER_POKEMON:
            continue
        per_anchor[row["pokemon_key"]] = seen + 1
        out.append(row)
    return out


def _slice_player_signature(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if (row.get("player_team_count") or 0) >= MIN_SIGNATURE_PLAYER_TEAMS
        and (row.get("player_pokemon_rank") or 0) <= MAX_SIGNATURE_PICKS_PER_PLAYER
    ]


MART_SLICERS = {
    "pokemon_team_synergy": _slice_team_synergy,
    "player_signature_pokemon": _slice_player_signature,
}


def to_pascal_case(slug: str) -> str:
    """Converts a hyphen-delimited PokéAPI form slug (e.g.
    "landorus-therian", "charizard-mega-x") into a PascalCase display name
    ("LandorusTherian", "CharizardMegaX") per the dashboard design system's
    Pokémon-naming convention (docs/design-system.md). Applied to
    pokemon_key/form_name rather than the raw species-only pokemon_name
    column, since form_name is what's actually unique per row — using the
    bare species name would collide across forms (e.g. Landorus-Incarnate
    and Landorus-Therian both reporting as "landorus")."""
    parts = [part for part in slug.split("-") if part]
    if not parts:
        return slug
    return "".join(part.capitalize() for part in parts)


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
    """Returns [] (not an error) if the mart's CSV doesn't exist yet.
    Marts listed in MART_SLICERS are cut down to the dashboard-relevant
    slice after coercion — see that dict's comment for why."""
    int_fields, float_fields = MART_FIELDS[mart_name]
    rows = _read_csv_rows(marts_dir / f"{mart_name}.csv")
    coerced = [_coerce(row, int_fields=int_fields, float_fields=float_fields) for row in rows]
    slicer = MART_SLICERS.get(mart_name)
    return slicer(coerced) if slicer else coerced


def load_pokemon_names(normalized_dir: Path = DEFAULT_NORMALIZED_DIR) -> dict[str, str]:
    """pokemon_key -> PascalCase display name, for friendlier labels than
    raw keys. Derived from pokemon_key itself (== form_name) via
    to_pascal_case rather than the CSV's own pokemon_name column, which is
    species-only and collides across a species' multiple forms. Returns {}
    gracefully if data/normalized/pokemon.csv isn't present."""
    return {
        row["pokemon_key"]: to_pascal_case(row["pokemon_key"])
        for row in _read_csv_rows(normalized_dir / "pokemon.csv")
    }


def load_marts(marts_dir: Path = DEFAULT_MARTS_DIR) -> dict[str, list[dict[str, Any]]]:
    return {mart_name: load_mart(marts_dir, mart_name) for mart_name in MART_FIELDS}


# <key column> -> <display-name column> pairs resolved against the
# pokemon_key -> PascalCase name map, so every mart row carries a
# ready-to-render name rather than each view looking it up client-side.
_NAME_JOINS = (
    ("pokemon_key", "pokemon_name"),
    ("partner_pokemon_key", "partner_pokemon_name"),
    ("opponent_pokemon_key", "opponent_pokemon_name"),
    ("best_matchup_pokemon_key", "best_matchup_pokemon_name"),
    ("worst_matchup_pokemon_key", "worst_matchup_pokemon_name"),
)


def _join_pokemon_names(
    marts: dict[str, list[dict[str, Any]]], pokemon_names: dict[str, str]
) -> dict[str, list[dict[str, Any]]]:
    joined = {}
    for mart_name, rows in marts.items():
        joined_rows = []
        for row in rows:
            for key_field, name_field in _NAME_JOINS:
                key = row.get(key_field)
                if key:
                    row = {**row, name_field: pokemon_names.get(key, key)}
            joined_rows.append(row)
        joined[mart_name] = joined_rows
    return joined


def compute_kpis(marts: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    usage_rows = [r for r in marts["pokemon_usage_summary"] if not r.get("event_tier")]
    legality_rows = marts["legality_summary_by_regulation"]
    win_rate_rows = marts["pokemon_win_rate_summary"]

    latest_snapshot_date = max((r["snapshot_date"] for r in legality_rows), default=None)
    legal_pool_by_regulation = [
        {
            "regulation_code": r["regulation_code"],
            "legal_pokemon_count": r["legal_pokemon_count"],
            "cumulative_legal_pokemon_count": r["cumulative_legal_pokemon_count"],
        }
        for r in legality_rows
        if r["snapshot_date"] == latest_snapshot_date
    ]

    top_used = min(usage_rows, key=lambda r: r["usage_rank"], default=None)

    # Ranked by wilson_rank (pokemon_win_rate_summary's Wilson score lower
    # bound, backlog.md #13) rather than raw win_rate, so a 1-0 record
    # doesn't outrank a well-established Pokémon's real win rate -- the
    # confidence interval accounts for sample size directly instead of
    # relying on an arbitrary record_count cutoff.
    top_win_rate = min(win_rate_rows, key=lambda r: r["wilson_rank"], default=None)

    # Overview tab spotlight grid (docs/design-system.md's "3-tier tab
    # layout convention"): drawn from the overall usage ranking, sliced to
    # a 6-wide-grid-friendly 12 -- the old Top 30 ranked list was removed
    # (dashboard "remove top 30 in overview" ask) since the grid tier
    # already covers the headline Pokémon and a full Usage-tab table
    # exists for raw drill-down. pokemon_usage_summary itself has no
    # win_rate column, so it's joined in here (win_rate stays None if the
    # Pokémon has no recorded win/loss data) -- otherwise every spotlight
    # card would show a uniform, uninformative "no win rate" placeholder.
    win_rate_by_key = {r["pokemon_key"]: r["win_rate"] for r in win_rate_rows}
    ranked_usage = sorted(usage_rows, key=lambda r: r["usage_rank"])
    ranked_usage = [{**r, "win_rate": win_rate_by_key.get(r["pokemon_key"])} for r in ranked_usage]
    top_12_pokemon = ranked_usage[:12]

    return {
        "latest_snapshot_date": latest_snapshot_date,
        "legal_pool_by_regulation": legal_pool_by_regulation,
        "distinct_pokemon_used": len(usage_rows),
        "top_used_pokemon": top_used,
        "top_win_rate_pokemon": top_win_rate,
        "top_12_pokemon": top_12_pokemon,
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
        "marts": marts,
        # Full pokemon_key -> display name map, needed client-side wherever
        # a row can't be joined 1:1 by _join_pokemon_names -- e.g.
        # top_tournament_teams' pipe-delimited pokemon_keys roster field,
        # and the pokepaste import/export + Matchup tab's ad-hoc species
        # lookups (docs/design-system.md's Top Teams / Matchup tabs).
        "pokemon_names": pokemon_names,
    }
