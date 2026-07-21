import csv
import json

import pytest

from pipelines.release import build


def _write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _passing_validation_report():
    return {
        "dataset_version": "0.1.0",
        "generated_at_utc": "2026-01-01T00:00:00Z",
        "coverage_checks": [
            {
                "check_name": "opgg_legal_pool_coverage",
                "description": "d",
                "threshold": ">=0.95",
                "metric_value": 0.98,
                "status": "pass",
            },
            {
                "check_name": "tournament_team_member_mapping_coverage",
                "description": "d",
                "threshold": ">=0.90",
                "metric_value": 0.99,
                "status": "pass",
            },
        ],
        "null_rate_checks": [
            {"table_name": t, "metric_value": 0.0, "threshold": "<=0.01", "status": "pass"}
            for t in build.TABLES
        ],
        "duplicate_key_checks": [
            {
                "table_name": t,
                "primary_key": pk,
                "duplicate_count": 0,
                "status": "pass",
            }
            for t, pk in build.TABLES.items()
        ],
        "referential_integrity_checks": [
            {"check_name": "some_check", "status": "pass", "violation_count": 0}
        ],
        "release_blocking_findings": [],
    }


def _populate_normalized_and_staging(tmp_path, *, include_missing_asset=False):
    normalized_dir = tmp_path / "normalized"
    staging_dir = tmp_path / "staging"
    asset_cache_dir = tmp_path / "assets" / "bulbagarden"
    for table_name, primary_key in build.TABLES.items():
        if table_name == "pokemon_asset":
            # pokemon_asset rows need a real local_cache_path so
            # _copy_referenced_images has something to copy.
            rows = [
                {primary_key: "k1", "local_cache_path": "0001.png"},
                {primary_key: "k2", "local_cache_path": "0002.png"},
            ]
            if include_missing_asset:
                # References a cache file that was never downloaded/was
                # pruned (coverage gate is only >=85%, not 100%).
                rows.append({primary_key: "k3", "local_cache_path": "0003.png"})
        else:
            rows = [{primary_key: "k1"}, {primary_key: "k2"}]
        _write_csv(normalized_dir / f"{table_name}.csv", rows)
    asset_cache_dir.mkdir(parents=True, exist_ok=True)
    (asset_cache_dir / "0001.png").write_bytes(b"fake-png-1")
    (asset_cache_dir / "0002.png").write_bytes(b"fake-png-2")
    _write_csv(
        staging_dir / "pokeapi.csv",
        [{"extracted_at_utc": "2026-01-01T00:00:00Z", "pokemon_id": "1"}],
    )
    _write_csv(
        staging_dir / "opgg_champions.csv",
        [{"extracted_at_utc": "2026-01-01T01:00:00Z", "pokemon_id": "1"}],
    )
    _write_csv(
        staging_dir / "munchstats.csv",
        [{"extracted_at_utc": "2026-01-01T02:00:00Z", "event_id": "e1"}],
    )
    _write_csv(
        staging_dir / "pokebase.csv",
        [{"extracted_at_utc": "2026-01-01T03:00:00Z", "pokemon_id": "1"}],
    )
    _write_csv(
        staging_dir / "bulbagarden.csv",
        [
            {
                "extracted_at_utc": "2026-01-01T04:00:00Z",
                "bulbagarden_title": "File:Menu CP 0001.png",
            }
        ],
    )
    return normalized_dir, staging_dir, asset_cache_dir


def test_build_raises_when_validation_report_missing(tmp_path):
    with pytest.raises(build.ReleaseBlockedError, match="not found"):
        build.build(
            "0.1.0",
            validation_report_path=tmp_path / "missing.json",
            normalized_dir=tmp_path / "normalized",
            staging_dir=tmp_path / "staging",
            releases_data_dir=tmp_path / "releases" / "data",
            manifests_dir=tmp_path / "releases" / "manifests",
            changelogs_dir=tmp_path / "releases" / "changelogs",
        )


def test_build_raises_when_gates_failing(tmp_path):
    report = _passing_validation_report()
    report["release_blocking_findings"] = ["pokemon: status=fail"]
    report_path = tmp_path / "validation_report.json"
    report_path.write_text(json.dumps(report))

    with pytest.raises(build.ReleaseBlockedError, match="pokemon: status=fail"):
        build.build(
            "0.1.0",
            validation_report_path=report_path,
            normalized_dir=tmp_path / "normalized",
            staging_dir=tmp_path / "staging",
            releases_data_dir=tmp_path / "releases" / "data",
            manifests_dir=tmp_path / "releases" / "manifests",
            changelogs_dir=tmp_path / "releases" / "changelogs",
        )


def test_build_writes_manifest_changelog_and_copies_tables(tmp_path):
    report_path = tmp_path / "validation_report.json"
    report_path.write_text(json.dumps(_passing_validation_report()))
    normalized_dir, staging_dir, asset_cache_dir = _populate_normalized_and_staging(tmp_path)
    releases_data_dir = tmp_path / "releases" / "data"
    manifests_dir = tmp_path / "releases" / "manifests"
    changelogs_dir = tmp_path / "releases" / "changelogs"

    manifest = build.build(
        "0.1.0",
        known_limitations=["example limitation"],
        validation_report_path=report_path,
        normalized_dir=normalized_dir,
        staging_dir=staging_dir,
        releases_data_dir=releases_data_dir,
        manifests_dir=manifests_dir,
        changelogs_dir=changelogs_dir,
        asset_cache_dir=asset_cache_dir,
    )

    assert manifest["dataset_version"] == "0.1.0"
    assert manifest["known_limitations"] == ["example limitation"]
    assert len(manifest["tables"]) == len(build.TABLES)
    assert all(t["row_count"] == 2 for t in manifest["tables"])
    assert {s["source_name"] for s in manifest["sources"]} == {
        "PokéAPI",
        "OP.GG Pokémon Champions",
        "MunchStats",
        "PokéBase",
        "Bulbagarden Archives",
    }
    assert manifest["images"] == {"count": 2, "missing": 0, "directory": "images/"}

    for table_name in build.TABLES:
        assert (releases_data_dir / "0.1.0" / f"{table_name}.csv").exists()

    images_dir = releases_data_dir / "0.1.0" / "images"
    assert (images_dir / "0001.png").read_bytes() == b"fake-png-1"
    assert (images_dir / "0002.png").read_bytes() == b"fake-png-2"

    manifest_path = manifests_dir / "manifest-0.1.0.json"
    assert manifest_path.exists()
    assert json.loads(manifest_path.read_text()) == manifest

    changelog_path = changelogs_dir / "CHANGELOG-0.1.0.md"
    assert changelog_path.exists()
    changelog_text = changelog_path.read_text()
    assert "dataset_version 0.1.0" in changelog_text
    assert "example limitation" in changelog_text
    assert "{VERSION}" not in changelog_text


def test_build_skips_missing_cached_images(tmp_path):
    report_path = tmp_path / "validation_report.json"
    report_path.write_text(json.dumps(_passing_validation_report()))
    normalized_dir, staging_dir, asset_cache_dir = _populate_normalized_and_staging(
        tmp_path, include_missing_asset=True
    )
    releases_data_dir = tmp_path / "releases" / "data"

    manifest = build.build(
        "0.1.0",
        validation_report_path=report_path,
        normalized_dir=normalized_dir,
        staging_dir=staging_dir,
        releases_data_dir=releases_data_dir,
        manifests_dir=tmp_path / "releases" / "manifests",
        changelogs_dir=tmp_path / "releases" / "changelogs",
        asset_cache_dir=asset_cache_dir,
    )

    assert manifest["images"] == {"count": 2, "missing": 1, "directory": "images/"}
    images_dir = releases_data_dir / "0.1.0" / "images"
    assert (images_dir / "0001.png").exists()
    assert (images_dir / "0002.png").exists()
    assert not (images_dir / "0003.png").exists()


def test_build_quality_checks_reflect_report(tmp_path):
    report = _passing_validation_report()
    report_path = tmp_path / "validation_report.json"
    report_path.write_text(json.dumps(report))
    normalized_dir, staging_dir, asset_cache_dir = _populate_normalized_and_staging(tmp_path)

    manifest = build.build(
        "0.2.0",
        validation_report_path=report_path,
        normalized_dir=normalized_dir,
        staging_dir=staging_dir,
        releases_data_dir=tmp_path / "releases" / "data",
        manifests_dir=tmp_path / "releases" / "manifests",
        changelogs_dir=tmp_path / "releases" / "changelogs",
        asset_cache_dir=asset_cache_dir,
    )

    checks_by_name = {c["check_name"]: c for c in manifest["quality_checks"]}
    assert checks_by_name["opgg_legal_pool_coverage"]["metric_value"] == 0.98
    assert checks_by_name["required_field_null_rate"]["status"] == "pass"
    assert checks_by_name["duplicate_primary_key_violations"]["metric_value"] == 0
    assert checks_by_name["referential_integrity"]["status"] == "pass"
