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


def _populate_marts(marts_dir, normalized_dir):
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
    _write_csv(
        marts_dir / "legality_summary_by_regulation.csv",
        [{"regulation_code": "m-a", "snapshot_date": "2026-01-01", "legal_pokemon_count": "2"}],
    )


def _build(marts_dir, normalized_dir, output_dir, **kwargs):
    # fetch_icons=False keeps these tests offline/deterministic — item-icon
    # resolution is the one part of a dashboard build that needs network
    # access (see pipelines/dashboard/build.py's _resolve_item_icons).
    kwargs.setdefault("fetch_icons", False)
    return build.build(
        marts_dir=marts_dir, normalized_dir=normalized_dir, output_dir=output_dir, **kwargs
    )


def test_build_writes_index_html_and_app_js(tmp_path):
    marts_dir = tmp_path / "marts"
    normalized_dir = tmp_path / "normalized"
    output_dir = tmp_path / "out"
    _populate_marts(marts_dir, normalized_dir)

    payload = _build(marts_dir, normalized_dir, output_dir)

    assert (output_dir / "index.html").exists()
    assert (output_dir / "app.js").exists()
    assert (output_dir / "app.js").read_bytes() == (build.STATIC_DIR / "app.js").read_bytes()

    html = (output_dir / "index.html").read_text(encoding="utf-8")
    embedded = _embedded_payload(html)
    assert embedded["kpis"]["distinct_pokemon_used"] == payload["kpis"]["distinct_pokemon_used"]
    assert "Pikachu" in html


def test_build_omits_removed_stat_change_and_trend_sections(tmp_path):
    marts_dir = tmp_path / "marts"
    normalized_dir = tmp_path / "normalized"
    output_dir = tmp_path / "out"
    _populate_marts(marts_dir, normalized_dir)

    _build(marts_dir, normalized_dir, output_dir)
    html = (output_dir / "index.html").read_text(encoding="utf-8")

    assert "Stat change leaderboard" not in html
    assert "Legal pool trend by regulation" not in html
    assert 'id="stat-change-table"' not in html
    assert 'id="legality-chart"' not in html


def test_build_has_tab_markup_for_all_five_tabs(tmp_path):
    marts_dir = tmp_path / "marts"
    normalized_dir = tmp_path / "normalized"
    output_dir = tmp_path / "out"
    _populate_marts(marts_dir, normalized_dir)

    _build(marts_dir, normalized_dir, output_dir)
    html = (output_dir / "index.html").read_text(encoding="utf-8")

    for tab in ("overview", "usage", "builds", "moves", "team-cores"):
        assert f'data-tab="{tab}"' in html
        assert f'data-panel="{tab}"' in html


def test_build_populates_sprites_and_type_icons(tmp_path):
    marts_dir = tmp_path / "marts"
    normalized_dir = tmp_path / "normalized"
    output_dir = tmp_path / "out"
    asset_cache_dir = tmp_path / "asset_cache"
    _populate_marts(marts_dir, normalized_dir)
    _write_csv(
        normalized_dir / "pokemon_asset.csv",
        [{"pokemon_key": "pikachu", "local_cache_path": "0025.png"}],
    )
    sprite_path = asset_cache_dir / "0025.png"
    sprite_path.parent.mkdir(parents=True, exist_ok=True)
    sprite_path.write_bytes(b"fake-png-bytes")

    payload = _build(marts_dir, normalized_dir, output_dir, asset_cache_dir=asset_cache_dir)

    assert payload["sprites"] == {"pikachu": "images/pikachu.png"}
    assert (output_dir / "images" / "pikachu.png").read_bytes() == b"fake-png-bytes"
    # raichu is referenced by pokemon_usage_summary but has no asset row,
    # so it's simply absent rather than raising.
    assert "raichu" not in payload["sprites"]

    assert set(payload["type_icons"].keys()) == {
        p.stem for p in (build.STATIC_ICONS_DIR / "types").glob("*.png")
    }
    for type_name, rel_path in payload["type_icons"].items():
        assert (output_dir / rel_path).exists()


def test_build_skips_item_icons_when_fetch_icons_false(tmp_path):
    marts_dir = tmp_path / "marts"
    normalized_dir = tmp_path / "normalized"
    output_dir = tmp_path / "out"
    _populate_marts(marts_dir, normalized_dir)

    payload = _build(marts_dir, normalized_dir, output_dir)

    assert payload["item_icons"] == {}
    assert not (output_dir / "images" / "icons" / "items").exists()


def test_safe_json_escapes_script_close_tag():
    payload = {"marts": {"pokemon_usage_summary": [{"pokemon_name": "</script><script>alert(1)"}]}}
    rendered = build._safe_json(payload)
    assert "</script>" not in rendered
    assert "\\u003c/script>" in rendered
