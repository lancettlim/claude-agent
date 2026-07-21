"""M6 dashboard analytics release (docs/todo.md, docs/prd.md milestone M6):
a first-party Streamlit dashboard on top of data/marts/*.csv and
data/normalized/pokemon.csv, covering the PRD's "Dashboard analytics
module" — KPI overview cards, trend views by regulation/tournament period,
and drill-down by Pokémon/item/ability/move.

Tech-stack/hosting decision (docs/todo.md M6 item, docs/prd.md open
question "Which dashboard tool stack and hosting model should be used for
Phase 1?"): Streamlit, reading the existing marts CSVs directly with no
new database or backend service. It's a pure-Python addition (fits this
repo's existing uv/Python tooling with no JS build step) and needs nothing
beyond `make dashboard` to run locally against a `make dbt-build` output.
Hosting is deliberately out of scope for this first pass — see the M6 items
in docs/todo.md for the follow-up on picking a public hosting target
(e.g. Streamlit Community Cloud) once there's a released dataset version
to host against.

Regulation scope: every Pokémon-level view (usage, win rate, item/ability/
move drill-down, stat leaderboard) is filtered to FOCUS_REGULATIONS' legal
pool (data/normalized/legality_snapshot.csv, not pokemon_stat_champions'
regulation-agnostic overall flag — see docs/dataset-spec.md's "Known
limitations (living)" section for why those two pools differ). This only
scopes the dashboard's default view; data/normalized/*.csv and
data/marts/*.csv themselves stay unfiltered so older/future-regulation
Pokémon remain available once a later regulation becomes current.

FOCUS_REGULATIONS is a list, not a single code, because Champions
regulations are cumulative here: m-b is an *extension* of m-a (it adds 39
newly-legal Pokémon on top of m-a's 268, not a replacement of them — the
two pools barely overlap), so the real current legal pool is their union
(306 Pokémon), not m-b alone. Bump the list (e.g. add "m-c") if a future
regulation is likewise additive; replace it entirely instead if a future
regulation ever turns out to *reset* the pool rather than extend it.

Run via `make dashboard` (`uv run streamlit run dashboard/app.py`).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[1]
MARTS_DIR = REPO_ROOT / "data" / "marts"
NORMALIZED_DIR = REPO_ROOT / "data" / "normalized"

# The Champions regulations whose union makes up the current legal pool
# (cumulative: m-b extends m-a rather than replacing it — see module
# docstring). The underlying data isn't filtered anywhere else, so older
# regulations stay available for historical use even as this list grows.
FOCUS_REGULATIONS = ["m-a", "m-b"]


@st.cache_data
def load_marts() -> dict[str, pd.DataFrame]:
    names = [
        "legality_summary_by_regulation",
        "pokemon_usage_summary",
        "stat_change_leaderboard",
        "pokemon_win_rate_summary",
        "pokemon_build_usage",
        "pokemon_move_usage",
    ]
    return {name: pd.read_csv(MARTS_DIR / f"{name}.csv") for name in names}


@st.cache_data
def load_pokemon_names() -> pd.DataFrame:
    pokemon = pd.read_csv(NORMALIZED_DIR / "pokemon.csv")
    return pokemon[["pokemon_key", "pokemon_name", "form_name"]].drop_duplicates("pokemon_key")


@st.cache_data
def load_legal_pool_keys(regulation_codes: list[str]) -> set[str]:
    """Union of pokemon_key sets legal under any of regulation_codes, each
    as of its own latest snapshot_date in legality_snapshot.csv
    (regulation-aware, unlike pokemon_stat_champions.is_legal — see
    docs/dataset-spec.md). Union, not intersection, because regulations
    here are cumulative (see FOCUS_REGULATIONS)."""
    snapshot = pd.read_csv(NORMALIZED_DIR / "legality_snapshot.csv")
    snapshot = snapshot[snapshot["regulation_code"].isin(regulation_codes)]
    if snapshot.empty:
        return set()
    latest_by_regulation = snapshot.groupby("regulation_code")["snapshot_date"].transform("max")
    current = snapshot[(snapshot["snapshot_date"] == latest_by_regulation) & (snapshot["is_legal"])]
    return set(current["pokemon_key"])


def with_display_name(df: pd.DataFrame, names: pd.DataFrame) -> pd.DataFrame:
    merged = df.merge(names, on="pokemon_key", how="left")
    merged["display_name"] = merged["form_name"].fillna(merged["pokemon_key"])
    return merged


st.set_page_config(page_title="Pokémon Champions Analytics", layout="wide")
st.title("Pokémon Champions Analytics")
FOCUS_LABEL = "+".join(FOCUS_REGULATIONS)
st.caption(
    f"Built from data/marts/*.csv, scoped to the current legal pool (regulations "
    f"**{FOCUS_LABEL}** — {FOCUS_REGULATIONS[-1]} extends {', '.join(FOCUS_REGULATIONS[:-1])} "
    "rather than replacing it) — run `make dbt-build` first if these tables look stale or missing."
)

try:
    marts = load_marts()
    names = load_pokemon_names()
    legal_pool = load_legal_pool_keys(FOCUS_REGULATIONS)
except FileNotFoundError as exc:
    st.error(
        f"Missing mart file: {exc}. Run `make dbt-build` (after `python -m pipelines.cli extract "
        "<source>` for each source) to populate data/marts/ and data/normalized/ before launching "
        "this dashboard."
    )
    st.stop()

if not legal_pool:
    st.warning(
        f"No legal Pokémon found for regulations {FOCUS_REGULATIONS!r} in "
        "data/normalized/legality_snapshot.csv — showing an empty dashboard. Check "
        "FOCUS_REGULATIONS in dashboard/app.py against the regulations "
        "legality_summary_by_regulation.csv reports."
    )

usage = with_display_name(marts["pokemon_usage_summary"], names)
usage = usage[usage["pokemon_key"].isin(legal_pool)]
win_rate = with_display_name(marts["pokemon_win_rate_summary"], names)
win_rate = win_rate[win_rate["pokemon_key"].isin(legal_pool)]
stat_leaderboard = with_display_name(marts["stat_change_leaderboard"], names)
stat_leaderboard = stat_leaderboard[stat_leaderboard["pokemon_key"].isin(legal_pool)]
legality = marts["legality_summary_by_regulation"]
build_usage = with_display_name(marts["pokemon_build_usage"], names)
build_usage = build_usage[build_usage["pokemon_key"].isin(legal_pool)]
move_usage = with_display_name(marts["pokemon_move_usage"], names)
move_usage = move_usage[move_usage["pokemon_key"].isin(legal_pool)]

overall_usage = usage[usage["event_tier"].isna()]

# --- KPI overview cards -----------------------------------------------------
kpi_cols = st.columns(4)
kpi_cols[0].metric(f"Legal Pokémon ({FOCUS_LABEL})", len(legal_pool))
kpi_cols[1].metric("Teams with usage data", int(overall_usage["usage_count"].sum()))
top_winner = win_rate.sort_values("win_rate", ascending=False).iloc[0] if len(win_rate) else None
kpi_cols[2].metric(
    "Top win rate",
    f"{top_winner['display_name']} ({top_winner['win_rate']:.0%})"
    if top_winner is not None
    else "n/a",
)
top_gainer = (
    stat_leaderboard[stat_leaderboard["direction"] == "gainer"]
    .sort_values("rank_within_direction")
    .iloc[0]
    if len(stat_leaderboard)
    else None
)
kpi_cols[3].metric(
    "Top stat gainer",
    f"{top_gainer['display_name']} (+{top_gainer['stat_total_delta']})"
    if top_gainer is not None
    else "n/a",
)

st.divider()

# --- Trend views: regulation window and tournament period -------------------
st.header("Trend views")
trend_cols = st.columns(2)

with trend_cols[0]:
    st.subheader("Legal pool size by regulation")
    st.caption(
        f"Shown for context across all regulations; **{FOCUS_LABEL}** (cumulative) is the current "
        "pool the rest of this dashboard is scoped to."
    )
    if legality["snapshot_date"].nunique() <= 1:
        st.caption(
            "Only one snapshot_date has been extracted so far, so this is a single-point-in-time "
            "view rather than a trend — see docs/dataset-spec.md's known limitations."
        )
    st.bar_chart(legality.set_index("regulation_code")["legal_pokemon_count"])

with trend_cols[1]:
    st.subheader("Usage by tournament tier")
    tiers = sorted(usage["event_tier"].dropna().unique())
    if tiers:
        selected_tier = st.selectbox("Tournament tier", tiers)
        tier_usage = (
            usage[usage["event_tier"] == selected_tier]
            .sort_values("usage_count", ascending=False)
            .head(15)
        )
        st.bar_chart(tier_usage.set_index("display_name")["usage_count"])
    else:
        st.caption("No tournament_event rows report an event_tier yet.")

st.divider()

# --- Overall usage and stat change leaderboard -------------------------------
leader_cols = st.columns(2)

with leader_cols[0]:
    st.subheader("Most-used Pokémon (overall)")
    st.dataframe(
        overall_usage.sort_values("usage_count", ascending=False).head(20)[
            ["display_name", "usage_count", "usage_rank"]
        ],
        hide_index=True,
    )

with leader_cols[1]:
    st.subheader("Stat change leaderboard")
    direction = st.radio("Direction", ["gainer", "loser"], horizontal=True)
    st.dataframe(
        stat_leaderboard[stat_leaderboard["direction"] == direction]
        .sort_values("rank_within_direction")
        .head(20)[["display_name", "stat_total_delta", "rank_within_direction"]],
        hide_index=True,
    )

st.divider()

# --- Drill-down by Pokémon: win rate, item/ability, moves --------------------
st.header("Pokémon drill-down")
legal_pool_names = with_display_name(
    pd.DataFrame({"pokemon_key": sorted(legal_pool)}), names
).sort_values("display_name")
selected_pokemon = st.selectbox("Pokémon", legal_pool_names["display_name"])
selected_key = legal_pool_names.loc[
    legal_pool_names["display_name"] == selected_pokemon, "pokemon_key"
].iloc[0]

drill_cols = st.columns(3)

with drill_cols[0]:
    st.subheader("Usage")
    row = overall_usage[overall_usage["pokemon_key"] == selected_key]
    if len(row):
        st.metric("Usage count", int(row["usage_count"].iloc[0]))
        st.metric("Usage rank", int(row["usage_rank"].iloc[0]))
    else:
        st.caption("No recorded tournament usage for this Pokémon yet.")

with drill_cols[1]:
    st.subheader("Win rate")
    row = win_rate[win_rate["pokemon_key"] == selected_key]
    if len(row):
        st.metric("Win rate", f"{row['win_rate'].iloc[0]:.0%}")
        st.metric(
            "Record (W-L)", f"{int(row['total_wins'].iloc[0])}-{int(row['total_losses'].iloc[0])}"
        )
    else:
        st.caption("No reported win/loss record for this Pokémon.")

with drill_cols[2]:
    st.subheader("Top item + ability")
    row = build_usage[build_usage["pokemon_key"] == selected_key].sort_values("usage_rank").head(1)
    if len(row):
        st.metric("Item", row["item_name"].iloc[0] or "n/a")
        st.metric("Ability", row["ability"].iloc[0] or "n/a")
    else:
        st.caption("No reported item/ability builds for this Pokémon.")

move_cols = st.columns(2)
with move_cols[0]:
    st.subheader("Top moves")
    st.dataframe(
        move_usage[move_usage["pokemon_key"] == selected_key]
        .sort_values("usage_rank")
        .head(10)[["move_name", "usage_count"]],
        hide_index=True,
    )
with move_cols[1]:
    st.subheader("Item + ability builds")
    st.dataframe(
        build_usage[build_usage["pokemon_key"] == selected_key]
        .sort_values("usage_rank")
        .head(10)[["item_name", "ability", "usage_count"]],
        hide_index=True,
    )
