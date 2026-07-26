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


def test_load_mart_coerces_archetype_marts(tmp_path):
    _write_csv(
        tmp_path / "pokemon_archetype_usage.csv",
        [
            {
                "archetype_key": "rain",
                "archetype_name": "Rain",
                "pokemon_key": "pelipper",
                "usage_share": "0.05",
                "win_rate": "0.5",
                "record_count": "100",
                "member_rank": "1",
            }
        ],
    )
    _write_csv(
        tmp_path / "archetype_summary.csv",
        [
            {
                "archetype_key": "rain",
                "archetype_name": "Rain",
                "member_count": "6",
                "combined_usage_share": "0.12",
                "avg_win_rate": "0.48",
                "top_member_pokemon_key": "pelipper",
            }
        ],
    )
    assert data.load_mart(tmp_path, "pokemon_archetype_usage") == [
        {
            "archetype_key": "rain",
            "archetype_name": "Rain",
            "pokemon_key": "pelipper",
            "usage_share": 0.05,
            "win_rate": 0.5,
            "record_count": 100,
            "member_rank": 1,
        }
    ]
    assert data.load_mart(tmp_path, "archetype_summary") == [
        {
            "archetype_key": "rain",
            "archetype_name": "Rain",
            "member_count": 6,
            "combined_usage_share": 0.12,
            "avg_win_rate": 0.48,
            "top_member_pokemon_key": "pelipper",
        }
    ]


def test_compute_kpis_top_12_and_top_30_and_cumulative_legal_pool():
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
    assert len(kpis["top_30_pokemon"]) == 30
    assert kpis["top_30_pokemon"][0]["pokemon_key"] == "mon-1"
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
