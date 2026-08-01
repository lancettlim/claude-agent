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
