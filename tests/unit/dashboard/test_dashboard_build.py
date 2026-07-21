import csv
import json

from pipelines.dashboard import build


def _write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _embedded_payload(html: str) -> dict:
    start = html.index("window.DASHBOARD_DATA = ") + len("window.DASHBOARD_DATA = ")
    end = html.index("</script>", start)
    raw = html[start:end].rstrip().rstrip(";")
    return json.loads(raw)


def _populate_marts(marts_dir, normalized_dir, *, degenerate=True):
    _write_csv(
        normalized_dir / "pokemon.csv",
        [
            {"pokemon_key": "pikachu", "pokemon_name": "Pikachu"},
            {"pokemon_key": "raichu", "pokemon_name": "Raichu"},
        ],
    )
    _write_csv(
        marts_dir / "pokemon_usage_summary.csv",
        [
            {"pokemon_key": "pikachu", "event_tier": "", "usage_count": "100", "usage_rank": "1"},
            {"pokemon_key": "raichu", "event_tier": "", "usage_count": "50", "usage_rank": "2"},
        ],
    )
    _write_csv(
        marts_dir / "pokemon_win_rate_summary.csv",
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
    _write_csv(
        marts_dir / "pokemon_build_usage.csv",
        [
            {
                "pokemon_key": "pikachu",
                "item_name": "Light Ball",
                "ability": "Static",
                "usage_count": "10",
                "usage_rank": "1",
            }
        ],
    )
    _write_csv(
        marts_dir / "pokemon_move_usage.csv",
        [
            {
                "pokemon_key": "pikachu",
                "move_name": "Thunderbolt",
                "usage_count": "8",
                "usage_rank": "1",
            }
        ],
    )
    if degenerate:
        _write_csv(
            marts_dir / "stat_change_leaderboard.csv",
            [
                {
                    "pokemon_key": "pikachu",
                    "stat_total_delta": "0",
                    "direction": "gainer",
                    "rank_within_direction": "1",
                }
            ],
        )
        _write_csv(
            marts_dir / "legality_summary_by_regulation.csv",
            [{"regulation_code": "m-a", "snapshot_date": "2026-01-01", "legal_pokemon_count": "2"}],
        )
    else:
        _write_csv(
            marts_dir / "stat_change_leaderboard.csv",
            [
                {
                    "pokemon_key": "pikachu",
                    "stat_total_delta": "5",
                    "direction": "gainer",
                    "rank_within_direction": "1",
                }
            ],
        )
        _write_csv(
            marts_dir / "legality_summary_by_regulation.csv",
            [
                {
                    "regulation_code": "m-a",
                    "snapshot_date": "2026-01-01",
                    "legal_pokemon_count": "2",
                },
                {
                    "regulation_code": "m-a",
                    "snapshot_date": "2026-02-01",
                    "legal_pokemon_count": "3",
                },
            ],
        )


def test_build_writes_index_html_and_app_js(tmp_path):
    marts_dir = tmp_path / "marts"
    normalized_dir = tmp_path / "normalized"
    output_dir = tmp_path / "out"
    _populate_marts(marts_dir, normalized_dir)

    payload = build.build(marts_dir=marts_dir, normalized_dir=normalized_dir, output_dir=output_dir)

    assert (output_dir / "index.html").exists()
    assert (output_dir / "app.js").exists()
    assert (output_dir / "app.js").read_bytes() == (build.STATIC_DIR / "app.js").read_bytes()

    html = (output_dir / "index.html").read_text(encoding="utf-8")
    embedded = _embedded_payload(html)
    assert embedded["kpis"]["distinct_pokemon_used"] == payload["kpis"]["distinct_pokemon_used"]
    assert "Pikachu" in html


def test_build_shows_empty_state_banners_when_degenerate(tmp_path):
    marts_dir = tmp_path / "marts"
    normalized_dir = tmp_path / "normalized"
    output_dir = tmp_path / "out"
    _populate_marts(marts_dir, normalized_dir, degenerate=True)

    build.build(marts_dir=marts_dir, normalized_dir=normalized_dir, output_dir=output_dir)
    html = (output_dir / "index.html").read_text(encoding="utf-8")

    assert "No stat rebalance data yet" in html
    assert "Trend views populate as more snapshots are collected" in html
    assert 'id="stat-change-table"' not in html
    assert 'id="legality-chart"' not in html


def test_build_omits_empty_state_banners_when_data_present(tmp_path):
    marts_dir = tmp_path / "marts"
    normalized_dir = tmp_path / "normalized"
    output_dir = tmp_path / "out"
    _populate_marts(marts_dir, normalized_dir, degenerate=False)

    build.build(marts_dir=marts_dir, normalized_dir=normalized_dir, output_dir=output_dir)
    html = (output_dir / "index.html").read_text(encoding="utf-8")

    assert "No stat rebalance data yet" not in html
    assert "Trend views populate as more snapshots are collected" not in html
    assert 'id="stat-change-table"' in html
    assert 'id="legality-chart"' in html


def test_safe_json_escapes_script_close_tag():
    payload = {"marts": {"pokemon_usage_summary": [{"pokemon_name": "</script><script>alert(1)"}]}}
    rendered = build._safe_json(payload)
    assert "</script>" not in rendered
    assert "\\u003c/script>" in rendered
