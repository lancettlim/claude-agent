"""Static Pokémon game-mechanic constants shared by both dashboard prototypes.

Not sourced/extracted data — these are fixed game rules (the type chart,
type colors, and the set of weather/terrain-setting abilities), so they
live as plain constants rather than going through the pipeline/marts. Both
dashboard/streamlit_app.py and dashboard/build_static.py import this
module directly (each script runs standalone, so a same-directory import
works without packaging); build_static.py additionally JSON-serializes
TYPE_COLORS/TYPE_CHART into the baked page so the static JS can compute
effectiveness client-side — keep any JS port of type_effectiveness()
mirroring the logic here exactly.
"""

from __future__ import annotations

POKEMON_TYPES = [
    "normal",
    "fire",
    "water",
    "electric",
    "grass",
    "ice",
    "fighting",
    "poison",
    "ground",
    "flying",
    "psychic",
    "bug",
    "rock",
    "ghost",
    "dragon",
    "dark",
    "steel",
    "fairy",
]

TYPE_COLORS: dict[str, str] = {
    "normal": "#A8A878",
    "fire": "#F08030",
    "water": "#6890F0",
    "electric": "#F8D030",
    "grass": "#78C850",
    "ice": "#98D8D8",
    "fighting": "#C03028",
    "poison": "#A040A0",
    "ground": "#E0C068",
    "flying": "#A890F0",
    "psychic": "#F85888",
    "bug": "#A8B820",
    "rock": "#B8A038",
    "ghost": "#705898",
    "dragon": "#7038F8",
    "dark": "#705848",
    "steel": "#B8B8D0",
    "fairy": "#EE99AC",
}


def _relative_luminance(hex_color: str) -> float:
    r, g, b = (int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5))

    def _linearize(channel: float) -> float:
        return channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4

    r, g, b = _linearize(r), _linearize(g), _linearize(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


# Badge text color per type, picked for contrast against TYPE_COLORS'
# background rather than hardcoded per-type (avoids 18 easy-to-get-wrong
# manual judgment calls).
TYPE_TEXT_COLORS: dict[str, str] = {
    type_name: ("#0b0b0b" if _relative_luminance(hex_color) > 0.5 else "#ffffff")
    for type_name, hex_color in TYPE_COLORS.items()
}

# Standard single-type-vs-single-type effectiveness chart:
# TYPE_CHART[attacking_type][defending_type] = multiplier. Omitted pairs
# default to 1.0 (neutral) via type_effectiveness()'s .get() lookups.
TYPE_CHART: dict[str, dict[str, float]] = {
    "normal": {"rock": 0.5, "ghost": 0.0, "steel": 0.5},
    "fire": {
        "fire": 0.5,
        "water": 0.5,
        "grass": 2.0,
        "ice": 2.0,
        "bug": 2.0,
        "rock": 0.5,
        "dragon": 0.5,
        "steel": 2.0,
    },
    "water": {"fire": 2.0, "water": 0.5, "grass": 0.5, "ground": 2.0, "rock": 2.0, "dragon": 0.5},
    "electric": {
        "water": 2.0,
        "electric": 0.5,
        "grass": 0.5,
        "ground": 0.0,
        "flying": 2.0,
        "dragon": 0.5,
    },
    "grass": {
        "fire": 0.5,
        "water": 2.0,
        "grass": 0.5,
        "poison": 0.5,
        "ground": 2.0,
        "flying": 0.5,
        "bug": 0.5,
        "rock": 2.0,
        "dragon": 0.5,
        "steel": 0.5,
    },
    "ice": {
        "fire": 0.5,
        "water": 0.5,
        "grass": 2.0,
        "ice": 0.5,
        "ground": 2.0,
        "flying": 2.0,
        "dragon": 2.0,
        "steel": 0.5,
    },
    "fighting": {
        "normal": 2.0,
        "ice": 2.0,
        "poison": 0.5,
        "flying": 0.5,
        "psychic": 0.5,
        "bug": 0.5,
        "rock": 2.0,
        "ghost": 0.0,
        "dark": 2.0,
        "steel": 2.0,
        "fairy": 0.5,
    },
    "poison": {
        "grass": 2.0,
        "poison": 0.5,
        "ground": 0.5,
        "rock": 0.5,
        "ghost": 0.5,
        "steel": 0.0,
        "fairy": 2.0,
    },
    "ground": {
        "fire": 2.0,
        "electric": 2.0,
        "grass": 0.5,
        "poison": 2.0,
        "flying": 0.0,
        "bug": 0.5,
        "rock": 2.0,
        "steel": 2.0,
    },
    "flying": {
        "electric": 0.5,
        "grass": 2.0,
        "fighting": 2.0,
        "bug": 2.0,
        "rock": 0.5,
        "steel": 0.5,
    },
    "psychic": {"fighting": 2.0, "poison": 2.0, "psychic": 0.5, "dark": 0.0, "steel": 0.5},
    "bug": {
        "fire": 0.5,
        "grass": 2.0,
        "fighting": 0.5,
        "poison": 0.5,
        "flying": 0.5,
        "psychic": 2.0,
        "ghost": 0.5,
        "dark": 2.0,
        "steel": 0.5,
        "fairy": 0.5,
    },
    "rock": {
        "fire": 2.0,
        "ice": 2.0,
        "fighting": 0.5,
        "ground": 0.5,
        "flying": 2.0,
        "bug": 2.0,
        "steel": 0.5,
    },
    "ghost": {"normal": 0.0, "psychic": 2.0, "ghost": 2.0, "dark": 0.5},
    "dragon": {"dragon": 2.0, "steel": 0.5, "fairy": 0.0},
    "dark": {"fighting": 0.5, "psychic": 2.0, "ghost": 2.0, "dark": 0.5, "fairy": 0.5},
    "steel": {
        "fire": 0.5,
        "water": 0.5,
        "electric": 0.5,
        "ice": 2.0,
        "rock": 2.0,
        "steel": 0.5,
        "fairy": 2.0,
    },
    "fairy": {
        "fire": 0.5,
        "fighting": 2.0,
        "poison": 0.5,
        "dragon": 2.0,
        "dark": 2.0,
        "steel": 0.5,
    },
}

# The 8 abilities that set weather or terrain on switch-in — powers the
# Weather/Terrain setter dashboard view.
WEATHER_TERRAIN_ABILITIES = {
    "Drizzle",
    "Drought",
    "Sand Stream",
    "Snow Warning",
    "Electric Surge",
    "Grassy Surge",
    "Psychic Surge",
    "Misty Surge",
}


def type_effectiveness(
    attacking_type: str, defending_type_1: str, defending_type_2: str | None = None
) -> float:
    """Multiplier for one attacking type against one or two defending types."""
    chart = TYPE_CHART.get(attacking_type, {})
    factor = chart.get(defending_type_1, 1.0)
    if defending_type_2:
        factor *= chart.get(defending_type_2, 1.0)
    return factor


def best_type_effectiveness(
    attacking_type_1: str,
    attacking_type_2: str | None,
    defending_type_1: str,
    defending_type_2: str | None = None,
) -> float:
    """Best of the attacker's one or two offensive typings against the
    defender's typing — the standard VGC convention for summarizing "how
    does A hit B" between two Pokémon that may each have 1 or 2 types.
    """
    best = type_effectiveness(attacking_type_1, defending_type_1, defending_type_2)
    if attacking_type_2:
        best = max(best, type_effectiveness(attacking_type_2, defending_type_1, defending_type_2))
    return best
