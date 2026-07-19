from game_data import (
    POKEMON_TYPES,
    TYPE_CHART,
    TYPE_COLORS,
    best_type_effectiveness,
    type_effectiveness,
)


def test_water_is_super_effective_against_fire():
    assert type_effectiveness("water", "fire") == 2.0


def test_electric_has_no_effect_on_ground():
    assert type_effectiveness("electric", "ground") == 0.0


def test_normal_is_quarter_effective_against_rock_steel_dual_type():
    assert type_effectiveness("normal", "rock", "steel") == 0.25


def test_normal_has_no_effect_on_ghost():
    assert type_effectiveness("normal", "ghost") == 0.0


def test_unlisted_matchup_defaults_to_neutral():
    assert type_effectiveness("fire", "electric") == 1.0


def test_best_type_effectiveness_takes_the_stronger_offensive_type():
    # Gyarados (water/flying) vs Landorus (ground/flying): water->ground=2x
    # is the attacker's best offensive typing (flying->ground is neutral).
    assert best_type_effectiveness("water", "flying", "ground", "flying") == 2.0


def test_best_type_effectiveness_single_attacking_type():
    assert best_type_effectiveness("water", None, "fire", None) == 2.0


def test_every_type_has_a_color_and_chart_entry():
    for type_name in POKEMON_TYPES:
        assert type_name in TYPE_COLORS
        assert TYPE_COLORS[type_name].startswith("#")
    # TYPE_CHART only lists non-neutral attacking types explicitly, but
    # every type does deal at least one non-neutral hit somewhere.
    assert set(TYPE_CHART.keys()) == set(POKEMON_TYPES)
