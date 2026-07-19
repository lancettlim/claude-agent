"""Streamlit dashboard prototype for the Pokémon Champions data platform.

M6 tech-stack comparison, Prototype A. Reads exclusively from
data/marts/*.csv (the Phase 3 flat analytical exports) — no other data
source. Run with:

    uv run streamlit run dashboard/streamlit_app.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[1]
MARTS_DIR = REPO_ROOT / "data" / "marts"


@st.cache_data
def load_marts() -> dict[str, pd.DataFrame]:
    return {
        "usage": pd.read_csv(MARTS_DIR / "pokemon_usage_summary.csv"),
        "win_rate": pd.read_csv(MARTS_DIR / "pokemon_win_rate_summary.csv"),
        "build": pd.read_csv(MARTS_DIR / "pokemon_build_usage.csv"),
        "move": pd.read_csv(MARTS_DIR / "pokemon_move_usage.csv"),
        "core": pd.read_csv(MARTS_DIR / "pokemon_team_core_usage.csv"),
        "legality": pd.read_csv(MARTS_DIR / "legality_summary_by_regulation.csv"),
        "stat_delta": pd.read_csv(MARTS_DIR / "stat_change_leaderboard.csv"),
    }


st.set_page_config(page_title="Pokémon Champions Dashboard", layout="wide")
data = load_marts()

st.title("Pokémon Champions Competitive Dashboard")
st.caption("Prototype A — Streamlit, reading data/marts/*.csv directly.")

overall_usage = data["usage"][data["usage"]["event_tier"].isna()]
tiers = sorted(data["usage"]["event_tier"].dropna().unique())
regulations = sorted(data["legality"]["regulation_code"].unique())

st.sidebar.header("Filters")
selected_tier = st.sidebar.selectbox("Tournament tier", ["All"] + tiers)
selected_regulation = st.sidebar.selectbox("Regulation", regulations)

usage_view = (
    overall_usage
    if selected_tier == "All"
    else data["usage"][data["usage"]["event_tier"] == selected_tier]
)

col1, col2, col3, col4 = st.columns(4)
legal_count = (
    data["legality"]
    .loc[data["legality"]["regulation_code"] == selected_regulation, "legal_pokemon_count"]
    .iloc[0]
)
top_used = usage_view.sort_values("usage_count", ascending=False).iloc[0]
top_win = data["win_rate"].sort_values("win_rate", ascending=False).iloc[0]
top_gainer = data["stat_delta"][data["stat_delta"]["direction"] == "gainer"].iloc[0]

col1.metric(f"Legal Pokémon ({selected_regulation})", int(legal_count))
col2.metric("Most-used Pokémon", top_used["pokemon_key"], f"{int(top_used['usage_count'])} uses")
col3.metric("Highest win rate", top_win["pokemon_key"], f"{top_win['win_rate']:.1%}")
col4.metric(
    "Top stat gainer", top_gainer["pokemon_key"], f"{int(top_gainer['stat_total_delta']):+d}"
)

st.divider()

left, right = st.columns(2)
with left:
    st.subheader("Legal-pool size by regulation")
    st.bar_chart(data["legality"].set_index("regulation_code")["legal_pokemon_count"])

with right:
    st.subheader(f"Top 15 used Pokémon ({selected_tier})")
    top15 = usage_view.sort_values("usage_count", ascending=False).head(15)
    st.bar_chart(top15.set_index("pokemon_key")["usage_count"])

st.divider()

st.subheader("Pokémon drill-down")
pokemon_options = sorted(overall_usage["pokemon_key"].unique())
selected_pokemon = st.selectbox("Choose a Pokémon", pokemon_options)

d1, d2, d3 = st.columns(3)
with d1:
    st.markdown("**Top items/abilities**")
    builds = (
        data["build"][data["build"]["pokemon_key"] == selected_pokemon]
        .sort_values("usage_rank")
        .head(8)
    )
    st.dataframe(builds[["item_name", "ability", "usage_count"]], hide_index=True)

with d2:
    st.markdown("**Top moves**")
    moves = (
        data["move"][data["move"]["pokemon_key"] == selected_pokemon]
        .sort_values("usage_rank")
        .head(8)
    )
    st.dataframe(moves[["move_name", "usage_count"]], hide_index=True)

with d3:
    st.markdown("**Top team cores**")
    core = (
        data["core"][
            (data["core"]["pokemon_key_a"] == selected_pokemon)
            | (data["core"]["pokemon_key_b"] == selected_pokemon)
        ]
        .sort_values("usage_count", ascending=False)
        .head(8)
        .copy()
    )
    core["partner"] = core.apply(
        lambda r: (
            r["pokemon_key_b"] if r["pokemon_key_a"] == selected_pokemon else r["pokemon_key_a"]
        ),
        axis=1,
    )
    st.dataframe(core[["partner", "usage_count"]], hide_index=True)

wr_row = data["win_rate"][data["win_rate"]["pokemon_key"] == selected_pokemon]
if not wr_row.empty:
    row = wr_row.iloc[0]
    st.caption(
        f"Win-rate proxy: {row['win_rate']:.1%} "
        f"({int(row['total_wins'])}W-{int(row['total_losses'])}L across "
        f"{int(row['record_count'])} recorded teams)"
    )
else:
    st.caption("No win-rate proxy data recorded for this Pokémon.")
