import csv

from pipelines.dashboard import data


def _write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_load_mart_returns_empty_list_when_file_missing(tmp_path):
    assert data.load_mart(tmp_path, "pokemon_usage_summary") == []


def test_load_mart_coerces_numeric_fields(tmp_path):
    _write_csv(
        tmp_path / "pokemon_win_rate_summary.csv",
        [
            {
                "pokemon_key": "pikachu",
                "total_wins": "10",
                "total_losses": "5",
                "win_rate": "0.6667",
                "record_count": "15",
                "wilson_lower_bound": "0.4",
                "wilson_rank": "1",
            }
        ],
    )
    rows = data.load_mart(tmp_path, "pokemon_win_rate_summary")
    assert rows == [
        {
            "pokemon_key": "pikachu",
            "total_wins": 10,
            "total_losses": 5,
            "win_rate": 0.6667,
            "record_count": 15,
            "wilson_lower_bound": 0.4,
            "wilson_rank": 1,
        }
    ]


def test_to_pascal_case():
    assert data.to_pascal_case("pikachu") == "Pikachu"
    assert data.to_pascal_case("landorus-therian") == "LandorusTherian"
    assert data.to_pascal_case("charizard-mega-x") == "CharizardMegaX"
    assert data.to_pascal_case("porygon-z") == "PorygonZ"


def test_load_pokemon_names_returns_empty_dict_when_file_missing(tmp_path):
    assert data.load_pokemon_names(tmp_path) == {}


def test_load_pokemon_names(tmp_path):
    # Display names are derived from pokemon_key (== form_name), not the
    # species-only pokemon_name column — landorus-therian's species-level
    # pokemon_name would just be "Landorus", which would collide with
    # Landorus-Incarnate's row if used directly.
    _write_csv(
        tmp_path / "pokemon.csv",
        [
            {"pokemon_key": "pikachu", "pokemon_name": "Pikachu"},
            {"pokemon_key": "landorus-therian", "pokemon_name": "Landorus"},
        ],
    )
    assert data.load_pokemon_names(tmp_path) == {
        "pikachu": "Pikachu",
        "landorus-therian": "LandorusTherian",
    }


def test_build_payload_joins_pokemon_names_and_computes_kpis(tmp_path):
    marts_dir = tmp_path / "marts"
    normalized_dir = tmp_path / "normalized"
    _write_csv(
        normalized_dir / "pokemon.csv",
        [{"pokemon_key": "pikachu", "pokemon_name": "Pikachu"}],
    )
    _write_csv(
        marts_dir / "pokemon_usage_summary.csv",
        [{"pokemon_key": "pikachu", "event_tier": "", "usage_count": "100", "usage_rank": "1"}],
    )
    # legality_summary_by_regulation, stat_change_leaderboard, etc. are left
    # unpopulated on purpose to exercise the missing-mart-file path.
    payload = data.build_payload(marts_dir, normalized_dir)

    assert payload["marts"]["pokemon_usage_summary"] == [
        {
            "pokemon_key": "pikachu",
            "event_tier": "",
            "usage_count": 100,
            "usage_rank": 1,
            "usage_share": None,
            "pokemon_name": "Pikachu",
        }
    ]
    assert payload["kpis"]["distinct_pokemon_used"] == 1
    assert payload["kpis"]["top_used_pokemon"]["pokemon_name"] == "Pikachu"
    assert payload["pokemon_names"] == {"pikachu": "Pikachu"}
    assert "generated_at_utc" in payload


def test_load_mart_coerces_usage_share(tmp_path):
    _write_csv(
        tmp_path / "pokemon_usage_summary.csv",
        [
            {
                "pokemon_key": "pikachu",
                "event_tier": "",
                "usage_count": "3",
                "usage_share": "0.75",
                "usage_rank": "1",
            }
        ],
    )
    rows = data.load_mart(tmp_path, "pokemon_usage_summary")
    assert rows[0]["usage_share"] == 0.75


def test_load_mart_coerces_champions_profile_fields(tmp_path):
    _write_csv(
        tmp_path / "pokemon_champions_profile.csv",
        [
            {
                "pokemon_key": "pikachu",
                "hp": "35",
                "attack": "55",
                "defense": "40",
                "sp_attack": "50",
                "sp_defense": "50",
                "speed": "90",
                "stat_total": "320",
                "usage_count": "3",
                "usage_share": "0.75",
                "win_rate": "0.6",
                "record_count": "5",
            }
        ],
    )
    rows = data.load_mart(tmp_path, "pokemon_champions_profile")
    assert rows == [
        {
            "pokemon_key": "pikachu",
            "hp": 35,
            "attack": 55,
            "defense": 40,
            "sp_attack": 50,
            "sp_defense": 50,
            "speed": 90,
            "stat_total": 320,
            "usage_count": 3,
            "usage_share": 0.75,
            "win_rate": 0.6,
            "record_count": 5,
        }
    ]


def test_load_mart_coerces_team_core_usage_fields(tmp_path):
    _write_csv(
        tmp_path / "pokemon_team_core_usage.csv",
        [
            {
                "pokemon_key": "pikachu",
                "partner_pokemon_key": "raichu",
                "co_occurrence_count": "3",
                "partner_share": "0.75",
                "usage_rank": "1",
            }
        ],
    )
    rows = data.load_mart(tmp_path, "pokemon_team_core_usage")
    assert rows == [
        {
            "pokemon_key": "pikachu",
            "partner_pokemon_key": "raichu",
            "co_occurrence_count": 3,
            "partner_share": 0.75,
            "usage_rank": 1,
        }
    ]


def test_load_mart_coerces_usage_by_event_date_fields(tmp_path):
    _write_csv(
        tmp_path / "pokemon_usage_by_event_date.csv",
        [
            {
                "pokemon_key": "incineroar",
                "event_date": "2026-07-01",
                "usage_count": "40",
                "usage_share": "0.4",
                "usage_rank": "1",
            }
        ],
    )
    rows = data.load_mart(tmp_path, "pokemon_usage_by_event_date")
    assert rows == [
        {
            "pokemon_key": "incineroar",
            "event_date": "2026-07-01",
            "usage_count": 40,
            "usage_share": 0.4,
            "usage_rank": 1,
        }
    ]


def test_load_mart_coerces_legality_cumulative_field(tmp_path):
    _write_csv(
        tmp_path / "legality_summary_by_regulation.csv",
        [
            {
                "regulation_code": "m-b",
                "snapshot_date": "2026-01-01",
                "legal_pokemon_count": "39",
                "cumulative_legal_pokemon_count": "307",
            }
        ],
    )
    rows = data.load_mart(tmp_path, "legality_summary_by_regulation")
    assert rows == [
        {
            "regulation_code": "m-b",
            "snapshot_date": "2026-01-01",
            "legal_pokemon_count": 39,
            "cumulative_legal_pokemon_count": 307,
        }
    ]


def test_load_mart_coerces_item_and_ability_usage_fields(tmp_path):
    _write_csv(
        tmp_path / "pokemon_item_usage.csv",
        [
            {
                "pokemon_key": "pikachu",
                "item_name": "Light Ball",
                "short_effect": "Doubles Attack and Special Attack.",
                "usage_count": "10",
                "item_share": "0.8",
                "usage_rank": "1",
            }
        ],
    )
    _write_csv(
        tmp_path / "pokemon_ability_usage.csv",
        [
            {
                "pokemon_key": "pikachu",
                "ability": "Static",
                "short_effect": "May paralyze on contact.",
                "usage_count": "10",
                "ability_share": "1.0",
                "usage_rank": "1",
            }
        ],
    )
    assert data.load_mart(tmp_path, "pokemon_item_usage") == [
        {
            "pokemon_key": "pikachu",
            "item_name": "Light Ball",
            "short_effect": "Doubles Attack and Special Attack.",
            "usage_count": 10,
            "item_share": 0.8,
            "usage_rank": 1,
        }
    ]
    assert data.load_mart(tmp_path, "pokemon_ability_usage") == [
        {
            "pokemon_key": "pikachu",
            "ability": "Static",
            "short_effect": "May paralyze on contact.",
            "usage_count": 10,
            "ability_share": 1.0,
            "usage_rank": 1,
        }
    ]


def test_load_mart_coerces_move_usage_detail_fields(tmp_path):
    _write_csv(
        tmp_path / "pokemon_move_usage.csv",
        [
            {
                "pokemon_key": "pikachu",
                "move_name": "Thunderbolt",
                "move_type": "electric",
                "power": "90",
                "accuracy": "100",
                "category": "special",
                "priority": "0",
                "pp": "15",
                "short_effect": "Has a 10% chance to paralyze.",
                "usage_count": "10",
                "move_share": "0.8",
                "usage_rank": "1",
            }
        ],
    )
    rows = data.load_mart(tmp_path, "pokemon_move_usage")
    assert rows == [
        {
            "pokemon_key": "pikachu",
            "move_name": "Thunderbolt",
            "move_type": "electric",
            "power": 90,
            "accuracy": 100,
            "category": "special",
            "priority": 0,
            "pp": 15,
            "short_effect": "Has a 10% chance to paralyze.",
            "usage_count": 10,
            "move_share": 0.8,
            "usage_rank": 1,
        }
    ]


def test_load_mart_coerces_top_tournament_teams_fields(tmp_path):
    _write_csv(
        tmp_path / "top_tournament_teams.csv",
        [
            {
                "team_id": "team-1",
                "event_name": "Regionals",
                "event_tier": "regional",
                "event_date": "2026-01-01",
                "player_name": "Ash",
                "player_country": "JP",
                "placement": "1",
                "record_wins": "7",
                "record_losses": "1",
                "win_rate": "0.875",
                "pokemon_keys": "pikachu|raichu",
                "team_rank": "1",
            }
        ],
    )
    rows = data.load_mart(tmp_path, "top_tournament_teams")
    assert rows == [
        {
            "team_id": "team-1",
            "event_name": "Regionals",
            "event_tier": "regional",
            "event_date": "2026-01-01",
            "player_name": "Ash",
            "player_country": "JP",
            "placement": 1,
            "record_wins": 7,
            "record_losses": 1,
            "win_rate": 0.875,
            "pokemon_keys": "pikachu|raichu",
            "team_rank": 1,
        }
    ]


def test_compute_kpis_top_12_and_cumulative_legal_pool():
    usage_rows = [
        {"pokemon_key": f"mon-{i}", "event_tier": "", "usage_rank": i, "usage_count": 100 - i}
        for i in range(1, 41)
    ]
    marts = {
        "pokemon_usage_summary": usage_rows,
        "legality_summary_by_regulation": [
            {
                "regulation_code": "m-a",
                "snapshot_date": "2026-01-01",
                "legal_pokemon_count": 268,
                "cumulative_legal_pokemon_count": 268,
            },
            {
                "regulation_code": "m-b",
                "snapshot_date": "2026-01-01",
                "legal_pokemon_count": 39,
                "cumulative_legal_pokemon_count": 307,
            },
        ],
        "pokemon_win_rate_summary": [],
    }
    kpis = data.compute_kpis(marts)

    assert [r["pokemon_key"] for r in kpis["top_12_pokemon"]] == [f"mon-{i}" for i in range(1, 13)]
    assert kpis["legal_pool_by_regulation"] == [
        {
            "regulation_code": "m-a",
            "legal_pokemon_count": 268,
            "cumulative_legal_pokemon_count": 268,
        },
        {
            "regulation_code": "m-b",
            "legal_pokemon_count": 39,
            "cumulative_legal_pokemon_count": 307,
        },
    ]


def test_join_pokemon_names_resolves_partner_pokemon_key(tmp_path):
    marts_dir = tmp_path / "marts"
    normalized_dir = tmp_path / "normalized"
    _write_csv(
        normalized_dir / "pokemon.csv",
        [
            {"pokemon_key": "pikachu", "pokemon_name": "Pikachu"},
            {"pokemon_key": "raichu", "pokemon_name": "Raichu"},
        ],
    )
    _write_csv(
        marts_dir / "pokemon_team_core_usage.csv",
        [
            {
                "pokemon_key": "pikachu",
                "partner_pokemon_key": "raichu",
                "co_occurrence_count": "3",
                "partner_share": "0.75",
                "usage_rank": "1",
            }
        ],
    )
    payload = data.build_payload(marts_dir, normalized_dir)

    assert payload["marts"]["pokemon_team_core_usage"] == [
        {
            "pokemon_key": "pikachu",
            "partner_pokemon_key": "raichu",
            "co_occurrence_count": 3,
            "partner_share": 0.75,
            "usage_rank": 1,
            "pokemon_name": "Pikachu",
            "partner_pokemon_name": "Raichu",
        }
    ]


def test_load_mart_coerces_speed_tier_bracket_fields(tmp_path):
    _write_csv(
        tmp_path / "pokemon_speed_tiers.csv",
        [
            {
                "pokemon_key": "dragapult",
                "type_1": "dragon",
                "type_2": "ghost",
                "base_speed": "142",
                "max_investment_speed": "213",
                "plus_one_speed": "319",
                "scarf_speed": "319",
                "plus_two_speed": "426",
                "tailwind_speed": "426",
                "scarf_tailwind_speed": "639",
                "usage_count": "40",
                "usage_share": "0.021",
                "win_rate": "0.51",
                "record_count": "80",
            }
        ],
    )
    rows = data.load_mart(tmp_path, "pokemon_speed_tiers")
    assert rows[0]["base_speed"] == 142
    assert rows[0]["max_investment_speed"] == 213
    assert rows[0]["scarf_tailwind_speed"] == 639
    assert rows[0]["usage_share"] == 0.021
    assert rows[0]["type_2"] == "ghost"


def test_load_mart_coerces_placement_weighted_usage_fields(tmp_path):
    _write_csv(
        tmp_path / "pokemon_placement_weighted_usage.csv",
        [
            {
                "pokemon_key": "incineroar",
                "usage_count": "1029",
                "top_cut_usage_count": "18",
                "top_cut_usage_share": "0.0721",
                "placement_weighted_score": "12.5",
                "weighted_usage_share": "0.0654",
                "weighted_usage_rank": "1",
            }
        ],
    )
    assert data.load_mart(tmp_path, "pokemon_placement_weighted_usage") == [
        {
            "pokemon_key": "incineroar",
            "usage_count": 1029,
            "top_cut_usage_count": 18,
            "top_cut_usage_share": 0.0721,
            "placement_weighted_score": 12.5,
            "weighted_usage_share": 0.0654,
            "weighted_usage_rank": 1,
        }
    ]


def test_load_mart_slices_team_synergy_to_the_dashboard_cut(tmp_path):
    # Pairs below MIN_SYNERGY_PAIR_TEAMS are dropped (lift is noise at that
    # sample size), and each anchor keeps at most
    # MAX_SYNERGY_PARTNERS_PER_POKEMON of its highest-lift partners.
    rows = [
        {
            "pokemon_key": "pikachu",
            "partner_pokemon_key": "partner-%02d" % i,
            "pair_team_count": "20",
            "lift": str(20 - i),
            "lift_rank": str(i + 1),
        }
        for i in range(15)
    ]
    rows.append(
        {
            "pokemon_key": "pikachu",
            "partner_pokemon_key": "rare-partner",
            "pair_team_count": "2",
            "lift": "99.0",
            "lift_rank": "16",
        }
    )
    _write_csv(tmp_path / "pokemon_team_synergy.csv", rows)

    sliced = data.load_mart(tmp_path, "pokemon_team_synergy")

    assert len(sliced) == data.MAX_SYNERGY_PARTNERS_PER_POKEMON
    partner_keys = [row["partner_pokemon_key"] for row in sliced]
    # The extreme-lift pair is excluded by the pair_team_count floor, not
    # kept because its lift is the highest in the file.
    assert "rare-partner" not in partner_keys
    assert partner_keys[0] == "partner-00"
    assert sliced[0]["lift"] == 20.0


def test_load_mart_slices_player_signature_to_established_players(tmp_path):
    _write_csv(
        tmp_path / "player_signature_pokemon.csv",
        [
            {
                "player_id": "established",
                "player_name": "Ash",
                "player_country": "JP",
                "player_team_count": "2",
                "pokemon_key": "pikachu",
                "usage_count": "11",
                "player_usage_share": "0.297",
                "player_pokemon_rank": "1",
            },
            {
                "player_id": "established",
                "player_name": "Ash",
                "player_country": "JP",
                "player_team_count": "2",
                "pokemon_key": "raichu",
                "usage_count": "1",
                "player_usage_share": "0.027",
                "player_pokemon_rank": "7",
            },
            {
                "player_id": "one-off",
                "player_name": "Gary",
                "player_country": "JP",
                "player_team_count": "1",
                "pokemon_key": "eevee",
                "usage_count": "1",
                "player_usage_share": "1.0",
                "player_pokemon_rank": "1",
            },
        ],
    )

    sliced = data.load_mart(tmp_path, "player_signature_pokemon")

    # A one-team player's 100% "signature" share is exactly the weak
    # evidence the floor exists to exclude; so is a rank-7 pick nothing
    # displays.
    assert [(row["player_id"], row["player_pokemon_rank"]) for row in sliced] == [
        ("established", 1)
    ]


def test_join_pokemon_names_resolves_matchup_summary_best_and_worst(tmp_path):
    marts_dir = tmp_path / "marts"
    normalized_dir = tmp_path / "normalized"
    _write_csv(
        normalized_dir / "pokemon.csv",
        [
            {"pokemon_key": "incineroar", "pokemon_name": "Incineroar"},
            {"pokemon_key": "torkoal", "pokemon_name": "Torkoal"},
            {"pokemon_key": "lycanroc-dusk", "pokemon_name": "Lycanroc"},
        ],
    )
    _write_csv(
        marts_dir / "pokemon_matchup_summary.csv",
        [
            {
                "pokemon_key": "incineroar",
                "overall_win_rate": "0.51",
                "distinct_opponents": "180",
                "total_matchup_appearances": "9000",
                "best_matchup_pokemon_key": "torkoal",
                "best_matchup_win_rate": "0.61",
                "best_matchup_matches": "290",
                "worst_matchup_pokemon_key": "lycanroc-dusk",
                "worst_matchup_win_rate": "0.391",
                "worst_matchup_matches": "289",
                "min_matches_threshold": "10",
            }
        ],
    )
    row = data.build_payload(marts_dir, normalized_dir)["marts"]["pokemon_matchup_summary"][0]

    assert row["pokemon_name"] == "Incineroar"
    assert row["best_matchup_pokemon_name"] == "Torkoal"
    # Display names come from pokemon_key via to_pascal_case, so the form
    # suffix survives — "LycanrocDusk", not the species-only "Lycanroc".
    assert row["worst_matchup_pokemon_name"] == "LycanrocDusk"


def test_join_pokemon_names_leaves_a_null_best_matchup_alone(tmp_path):
    # pokemon_matchup_summary left-joins best/worst, so a Pokémon with no
    # qualifying opponent has null keys — those must not resolve to a
    # display name at all rather than to an empty-string one.
    marts_dir = tmp_path / "marts"
    normalized_dir = tmp_path / "normalized"
    _write_csv(
        normalized_dir / "pokemon.csv",
        [{"pokemon_key": "pikachu", "pokemon_name": "Pikachu"}],
    )
    _write_csv(
        marts_dir / "pokemon_matchup_summary.csv",
        [
            {
                "pokemon_key": "pikachu",
                "overall_win_rate": "0.5",
                "distinct_opponents": "1",
                "total_matchup_appearances": "2",
                "best_matchup_pokemon_key": "",
                "best_matchup_win_rate": "",
                "best_matchup_matches": "",
                "worst_matchup_pokemon_key": "",
                "worst_matchup_win_rate": "",
                "worst_matchup_matches": "",
                "min_matches_threshold": "10",
            }
        ],
    )
    row = data.build_payload(marts_dir, normalized_dir)["marts"]["pokemon_matchup_summary"][0]

    assert "best_matchup_pokemon_name" not in row
    assert "worst_matchup_pokemon_name" not in row
    assert row["best_matchup_win_rate"] is None
