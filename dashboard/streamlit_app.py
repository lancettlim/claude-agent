"""Streamlit dashboard prototype for the Pokémon Champions data platform.

M6 tech-stack comparison, Prototype A. Reads exclusively from
data/marts/*.csv (the Phase 3 flat analytical exports) — no other data
source, aside from dashboard/game_data.py's static game-mechanic
constants (type chart/colors, weather/terrain abilities). Run with:

    uv run streamlit run dashboard/streamlit_app.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st
from game_data import (
    TYPE_COLORS,
    TYPE_TEXT_COLORS,
    WEATHER_TERRAIN_ABILITIES,
    best_type_effectiveness,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
MARTS_DIR = REPO_ROOT / "data" / "marts"

STAT_COLUMNS = ["hp", "attack", "defense", "sp_attack", "sp_defense", "speed", "stat_total"]


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
        "stat_profile": pd.read_csv(MARTS_DIR / "pokemon_stat_profile.csv"),
        "tera": pd.read_csv(MARTS_DIR / "pokemon_tera_type_usage.csv"),
        "ability": pd.read_csv(MARTS_DIR / "pokemon_ability_usage.csv"),
    }


def type_badge_html(type_name: str | float) -> str:
    if pd.isna(type_name):
        return ""
    bg = TYPE_COLORS.get(type_name, "#888888")
    fg = TYPE_TEXT_COLORS.get(type_name, "#ffffff")
    return (
        f'<span style="background:{bg}; color:{fg}; padding:2px 8px; '
        f'border-radius:999px; font-size:0.72rem; margin-right:4px;">{type_name}</span>'
    )


def type_badges_html(type_1: str, type_2: str | float) -> str:
    return type_badge_html(type_1) + type_badge_html(type_2)


def types_display(row: pd.Series) -> str:
    if pd.isna(row["type_1"]):
        return ""
    return row["type_1"] + (f" / {row['type_2']}" if pd.notna(row["type_2"]) else "")


def image_column(label: str = "") -> st.column_config.ImageColumn:
    return st.column_config.ImageColumn(label, width="small")


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

st.subheader("Speed Tier List")
st.caption("Base speed (Champions-format stats — no EVs, nature, or items modeled).")
speed_tiers = data["stat_profile"].sort_values("speed", ascending=False).copy()
speed_tiers["types"] = speed_tiers.apply(types_display, axis=1)
st.dataframe(
    speed_tiers[["image_url", "pokemon_key", "types", "speed", "stat_total"]],
    column_config={
        "image_url": image_column(),
        "pokemon_key": "Pokémon",
        "types": "Type(s)",
        "speed": "Speed",
        "stat_total": "BST",
    },
    hide_index=True,
    height=400,
)

st.divider()

st.subheader("Stat Comparison")
stat_profile_options = sorted(data["stat_profile"]["pokemon_key"].unique())
cmp_a_col, cmp_b_col = st.columns(2)
pokemon_a = cmp_a_col.selectbox("Pokémon A", stat_profile_options, index=0, key="cmp_a")
default_b_index = 1 if len(stat_profile_options) > 1 else 0
pokemon_b = cmp_b_col.selectbox(
    "Pokémon B", stat_profile_options, index=default_b_index, key="cmp_b"
)

row_a = data["stat_profile"][data["stat_profile"]["pokemon_key"] == pokemon_a].iloc[0]
row_b = data["stat_profile"][data["stat_profile"]["pokemon_key"] == pokemon_b].iloc[0]

with cmp_a_col:
    if pd.notna(row_a["image_url"]):
        st.image(row_a["image_url"], width=120)
    st.markdown(
        f"**{pokemon_a}**  \n{type_badges_html(row_a['type_1'], row_a['type_2'])}",
        unsafe_allow_html=True,
    )
with cmp_b_col:
    if pd.notna(row_b["image_url"]):
        st.image(row_b["image_url"], width=120)
    st.markdown(
        f"**{pokemon_b}**  \n{type_badges_html(row_b['type_1'], row_b['type_2'])}",
        unsafe_allow_html=True,
    )

base_stat_columns = [c for c in STAT_COLUMNS if c != "stat_total"]
comparison_df = pd.DataFrame(
    {pokemon_a: row_a[base_stat_columns].values, pokemon_b: row_b[base_stat_columns].values},
    index=base_stat_columns,
)
st.bar_chart(comparison_df)
st.caption(f"BST: {pokemon_a} {int(row_a['stat_total'])} · {pokemon_b} {int(row_b['stat_total'])}")

type_2_a = row_a["type_2"] if pd.notna(row_a["type_2"]) else None
type_2_b = row_b["type_2"] if pd.notna(row_b["type_2"]) else None
eff_a_to_b = best_type_effectiveness(row_a["type_1"], type_2_a, row_b["type_1"], type_2_b)
eff_b_to_a = best_type_effectiveness(row_b["type_1"], type_2_b, row_a["type_1"], type_2_a)
st.caption(
    f"{pokemon_a}'s types are {eff_a_to_b}× effective against {pokemon_b}. "
    f"{pokemon_b}'s types are {eff_b_to_a}× effective against {pokemon_a}."
)

st.divider()

st.subheader("Speed Control")
sc1, sc2, sc3 = st.columns(3)
with sc1:
    st.markdown("**Choice Scarf users**")
    scarf = (
        data["build"][data["build"]["item_name"] == "Choice Scarf"]
        .merge(data["stat_profile"][["pokemon_key", "image_url"]], on="pokemon_key", how="left")
        .sort_values("usage_count", ascending=False)
        .head(10)
    )
    st.dataframe(
        scarf[["image_url", "pokemon_key", "usage_count"]],
        column_config={
            "image_url": image_column(),
            "pokemon_key": "Pokémon",
            "usage_count": "Uses",
        },
        hide_index=True,
    )
with sc2:
    st.markdown("**Tailwind setters**")
    tailwind = (
        data["move"][data["move"]["move_name"] == "Tailwind"]
        .merge(data["stat_profile"][["pokemon_key", "image_url"]], on="pokemon_key", how="left")
        .sort_values("usage_count", ascending=False)
        .head(10)
    )
    st.dataframe(
        tailwind[["image_url", "pokemon_key", "usage_count"]],
        column_config={
            "image_url": image_column(),
            "pokemon_key": "Pokémon",
            "usage_count": "Uses",
        },
        hide_index=True,
    )
with sc3:
    st.markdown("**Trick Room setters**")
    trick_room = (
        data["move"][data["move"]["move_name"] == "Trick Room"]
        .merge(data["stat_profile"][["pokemon_key", "image_url"]], on="pokemon_key", how="left")
        .sort_values("usage_count", ascending=False)
        .head(10)
    )
    st.dataframe(
        trick_room[["image_url", "pokemon_key", "usage_count"]],
        column_config={
            "image_url": image_column(),
            "pokemon_key": "Pokémon",
            "usage_count": "Uses",
        },
        hide_index=True,
    )

st.divider()

st.subheader("Weather / Terrain Setters")
weather = (
    data["ability"][data["ability"]["ability"].isin(WEATHER_TERRAIN_ABILITIES)]
    .merge(data["stat_profile"][["pokemon_key", "image_url"]], on="pokemon_key", how="left")
    .sort_values("usage_count", ascending=False)
)
st.dataframe(
    weather[["image_url", "pokemon_key", "ability", "usage_count"]],
    column_config={
        "image_url": image_column(),
        "pokemon_key": "Pokémon",
        "ability": "Ability",
        "usage_count": "Uses",
    },
    hide_index=True,
)

st.divider()

st.subheader("Meta Tier List")
st.caption("Sorted by usage; click a column header to re-sort. No invented letter grades.")
meta = overall_usage.merge(
    data["win_rate"][["pokemon_key", "win_rate", "record_count"]], on="pokemon_key", how="left"
).merge(
    data["stat_profile"][["pokemon_key", "image_url", "type_1", "type_2"]],
    on="pokemon_key",
    how="left",
)
meta["types"] = meta.apply(types_display, axis=1)
meta["win_rate_pct"] = meta["win_rate"] * 100
st.dataframe(
    meta[
        [
            "image_url",
            "pokemon_key",
            "types",
            "usage_rank",
            "usage_count",
            "win_rate_pct",
            "record_count",
        ]
    ].sort_values("usage_rank"),
    column_config={
        "image_url": image_column(),
        "pokemon_key": "Pokémon",
        "types": "Type(s)",
        "usage_rank": "Usage Rank",
        "usage_count": "Uses",
        "win_rate_pct": st.column_config.NumberColumn("Win Rate", format="%.1f%%"),
        "record_count": "Recorded Teams",
    },
    hide_index=True,
    height=400,
)

st.divider()

st.subheader("Pokémon drill-down")
pokemon_options = sorted(overall_usage["pokemon_key"].unique())
selected_pokemon = st.selectbox("Choose a Pokémon", pokemon_options)

profile_row = data["stat_profile"][data["stat_profile"]["pokemon_key"] == selected_pokemon]
if not profile_row.empty:
    profile = profile_row.iloc[0]
    hero_col, info_col = st.columns([1, 3])
    with hero_col:
        if pd.notna(profile["image_url"]):
            st.image(profile["image_url"], width=140)
    with info_col:
        st.markdown(
            f"### {selected_pokemon}  \n{type_badges_html(profile['type_1'], profile['type_2'])}",
            unsafe_allow_html=True,
        )
        st.caption(
            f"HP {profile['hp']} · Atk {profile['attack']} · Def {profile['defense']} · "
            f"SpA {profile['sp_attack']} · SpD {profile['sp_defense']} · Spe {profile['speed']} · "
            f"BST {profile['stat_total']}"
        )

d1, d2, d3, d4 = st.columns(4)
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

with d4:
    st.markdown("**Top Tera types**")
    tera = (
        data["tera"][data["tera"]["pokemon_key"] == selected_pokemon]
        .sort_values("usage_rank")
        .head(8)
    )
    st.dataframe(tera[["tera_type", "usage_count"]], hide_index=True)

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
