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


def test_load_pokemon_names_returns_empty_dict_when_file_missing(tmp_path):
    assert data.load_pokemon_names(tmp_path) == {}


def test_load_pokemon_names(tmp_path):
    _write_csv(
        tmp_path / "pokemon.csv",
        [{"pokemon_key": "pikachu", "pokemon_name": "Pikachu"}],
    )
    assert data.load_pokemon_names(tmp_path) == {"pikachu": "Pikachu"}


def test_compute_flags_stat_changes_degenerate_when_all_zero():
    marts = {
        "stat_change_leaderboard": [
            {"pokemon_key": "a", "stat_total_delta": 0, "direction": "gainer"},
            {"pokemon_key": "b", "stat_total_delta": 0, "direction": "gainer"},
        ],
        "legality_summary_by_regulation": [
            {"regulation_code": "m-a", "snapshot_date": "2026-01-01", "legal_pokemon_count": 10}
        ],
    }
    flags = data.compute_flags(marts)
    assert flags["stat_changes_degenerate"] is True
    assert flags["trend_degenerate"] is True


def test_compute_flags_not_degenerate_with_mixed_deltas_and_multiple_dates():
    marts = {
        "stat_change_leaderboard": [
            {"pokemon_key": "a", "stat_total_delta": 5, "direction": "gainer"},
            {"pokemon_key": "b", "stat_total_delta": -3, "direction": "loser"},
        ],
        "legality_summary_by_regulation": [
            {"regulation_code": "m-a", "snapshot_date": "2026-01-01", "legal_pokemon_count": 10},
            {"regulation_code": "m-a", "snapshot_date": "2026-02-01", "legal_pokemon_count": 12},
        ],
    }
    flags = data.compute_flags(marts)
    assert flags["stat_changes_degenerate"] is False
    assert flags["trend_degenerate"] is False


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
            "pokemon_name": "Pikachu",
        }
    ]
    assert payload["kpis"]["distinct_pokemon_used"] == 1
    assert payload["kpis"]["top_used_pokemon"]["pokemon_name"] == "Pikachu"
    assert payload["flags"]["stat_changes_degenerate"] is True
    assert payload["flags"]["trend_degenerate"] is True
    assert "generated_at_utc" in payload
