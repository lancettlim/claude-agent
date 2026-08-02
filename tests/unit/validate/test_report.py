import json

import duckdb
import pytest

from pipelines.validate import report


def _manifest_node(name: str, meta: dict | None = None) -> dict:
    return {
        "resource_type": "test",
        "name": name,
        "config": {"meta": meta or {}},
    }


def _run_result(unique_id: str, status: str, failures) -> dict:
    return {"unique_id": unique_id, "status": status, "failures": failures}


def _template() -> dict:
    path = report.REPO_ROOT / "reports" / "validation" / "validation_report.template.json"
    return json.loads(path.read_text())


def test_build_report_matches_template_shape():
    manifest = {
        "nodes": {
            "test.pokemon_champions.assert_duplicate_key_pokemon.abc123": _manifest_node(
                "assert_duplicate_key_pokemon",
                {
                    "category": "duplicate_key",
                    "table_name": "pokemon",
                    "primary_key": "pokemon_key",
                },
            ),
            "test.pokemon_champions.assert_null_rate_pokemon.def456": _manifest_node(
                "assert_null_rate_pokemon", {"category": "null_rate", "table_name": "pokemon"}
            ),
            "test.pokemon_champions.assert_pokemon_stat_canonical_resolves_to_pokemon.ghi789": (
                _manifest_node(
                    "assert_pokemon_stat_canonical_resolves_to_pokemon",
                    {
                        "category": "referential_integrity",
                        "check_name": "pokemon_stat_canonical_resolves_to_pokemon",
                    },
                )
            ),
            "test.pokemon_champions.assert_opgg_legal_pool_coverage.jkl012": _manifest_node(
                "assert_opgg_legal_pool_coverage",
                {
                    "category": "coverage",
                    "check_name": "opgg_legal_pool_coverage",
                    "description": "Share of OP.GG legal pool rows mapped to a canonical pokemon_id",
                    "threshold": ">=0.95",
                },
            ),
            "model.pokemon_champions.pokemon": {"resource_type": "model", "name": "pokemon"},
        }
    }
    run_results = {
        "results": [
            _run_result("test.pokemon_champions.assert_duplicate_key_pokemon.abc123", "pass", 0),
            _run_result("test.pokemon_champions.assert_null_rate_pokemon.def456", "fail", 200),
            _run_result(
                "test.pokemon_champions.assert_pokemon_stat_canonical_resolves_to_pokemon.ghi789",
                "pass",
                0,
            ),
            _run_result(
                "test.pokemon_champions.assert_opgg_legal_pool_coverage.jkl012", "pass", 10000
            ),
        ]
    }

    result = report.build_report(
        manifest, run_results, dataset_version="0.1.0", warehouse_path=None
    )
    template = _template()

    assert set(result) == set(template)

    pokemon_dup_check = next(
        c for c in result["duplicate_key_checks"] if c["table_name"] == "pokemon"
    )
    assert pokemon_dup_check["status"] == "pass"
    assert pokemon_dup_check["duplicate_count"] == 0
    assert pokemon_dup_check["primary_key"] == "pokemon_key"

    pokemon_null_check = next(c for c in result["null_rate_checks"] if c["table_name"] == "pokemon")
    assert pokemon_null_check["status"] == "fail"
    assert pokemon_null_check["metric_value"] == 0.02

    opgg_coverage_check = next(
        c for c in result["coverage_checks"] if c["check_name"] == "opgg_legal_pool_coverage"
    )
    assert opgg_coverage_check["metric_value"] == 1.0

    assert result["uncategorized_checks"] == []
    assert "pokemon: status=fail" in result["release_blocking_findings"]


def test_build_report_marks_unresulted_tests_as_skipped():
    manifest = {
        "nodes": {
            "test.pokemon_champions.assert_duplicate_key_pokemon.abc123": _manifest_node(
                "assert_duplicate_key_pokemon",
                {
                    "category": "duplicate_key",
                    "table_name": "pokemon",
                    "primary_key": "pokemon_key",
                },
            ),
        }
    }
    result = report.build_report(
        manifest, {"results": []}, dataset_version="0.1.0", warehouse_path=None
    )

    assert len(result["duplicate_key_checks"]) == 1
    check = result["duplicate_key_checks"][0]
    assert check["status"] == "skipped"
    assert check["duplicate_count"] is None
    assert result["release_blocking_findings"] == []


def test_build_freshness_checks_returns_empty_list_when_not_run():
    assert report.build_freshness_checks(None) == []


def test_build_freshness_checks_reshapes_sources_json():
    sources_result = {
        "results": [
            {
                "unique_id": "source.pokemon_champions.staging.opgg_champions",
                "status": "pass",
                "max_loaded_at": "2026-08-01T00:00:00+00:00",
                "max_loaded_at_time_ago_in_s": 3600.0,
            },
            {
                "unique_id": "source.pokemon_champions.staging.munchstats",
                "status": "error",
                "max_loaded_at": "2026-07-20T00:00:00+00:00",
                "max_loaded_at_time_ago_in_s": 999999.0,
            },
        ]
    }

    checks = report.build_freshness_checks(sources_result)

    assert checks == [
        {
            "source_name": "munchstats",
            "status": "fail",
            "max_loaded_at": "2026-07-20T00:00:00+00:00",
            "age_hours": round(999999.0 / 3600, 1),
        },
        {
            "source_name": "opgg_champions",
            "status": "pass",
            "max_loaded_at": "2026-08-01T00:00:00+00:00",
            "age_hours": 1.0,
        },
    ]


def test_build_report_folds_freshness_failures_into_release_blocking_findings():
    sources_result = {
        "results": [
            {
                "unique_id": "source.pokemon_champions.staging.munchstats",
                "status": "error",
                "max_loaded_at": None,
                "max_loaded_at_time_ago_in_s": None,
            },
        ]
    }

    result = report.build_report(
        {"nodes": {}},
        {"results": []},
        dataset_version="0.1.0",
        sources_result=sources_result,
        warehouse_path=None,
    )

    assert result["freshness_checks"] == [
        {
            "source_name": "munchstats",
            "status": "fail",
            "max_loaded_at": None,
            "age_hours": None,
        }
    ]
    assert "munchstats: status=fail" in result["release_blocking_findings"]


def test_build_report_categorizes_row_count_anomaly_checks():
    manifest = {
        "nodes": {
            "test.pokemon_champions.source_row_count_anomaly_staging_munchstats.abc123": (
                _manifest_node(
                    "source_row_count_anomaly_staging_munchstats",
                    {"category": "row_count_anomaly", "source_name": "munchstats"},
                )
            ),
        }
    }
    run_results = {
        "results": [
            _run_result(
                "test.pokemon_champions.source_row_count_anomaly_staging_munchstats.abc123",
                "fail",
                2000,
            ),
        ]
    }

    result = report.build_report(
        manifest, run_results, dataset_version="0.1.0", warehouse_path=None
    )
    template = _template()

    assert set(result) == set(template)
    assert result["row_count_anomaly_checks"] == [
        {
            "source_name": "munchstats",
            "metric_value": 0.2,
            "threshold": ">=0.5x previous snapshot",
            "status": "fail",
        }
    ]
    assert "munchstats: status=fail" in result["release_blocking_findings"]


def _write_schema(path, field_names):
    path.write_text(json.dumps({"fields": [{"name": n, "required": True} for n in field_names]}))


def _write_csv(path, header):
    path.write_text(",".join(header) + "\n")


def test_build_schema_drift_checks_pass_when_header_matches_schema(tmp_path):
    _write_schema(tmp_path / "pokemon.schema.json", ["pokemon_key", "pokemon_name"])
    _write_csv(tmp_path / "pokemon.csv", ["pokemon_key", "pokemon_name"])

    checks = report.build_schema_drift_checks(tmp_path)

    assert checks == [
        {
            "table_name": "pokemon",
            "status": "pass",
            "expected_fields": ["pokemon_key", "pokemon_name"],
            "actual_fields": ["pokemon_key", "pokemon_name"],
        }
    ]


def test_build_schema_drift_checks_fails_on_renamed_column(tmp_path):
    """A column rename (or add/drop/reorder) must be caught here, not
    silently propagate through the normalized layer's bare `select *`
    staging models (backlog.md #41)."""
    _write_schema(tmp_path / "pokemon.schema.json", ["pokemon_key", "pokemon_name"])
    _write_csv(tmp_path / "pokemon.csv", ["pokemon_key", "species_name"])

    checks = report.build_schema_drift_checks(tmp_path)

    assert checks[0]["status"] == "fail"
    assert checks[0]["expected_fields"] == ["pokemon_key", "pokemon_name"]
    assert checks[0]["actual_fields"] == ["pokemon_key", "species_name"]


def test_build_schema_drift_checks_skipped_when_csv_missing(tmp_path):
    """A schema.json with no matching .csv yet (fresh clone, no dbt build,
    or a source like Bulbagarden that hasn't been extracted) is a
    different case from a real mismatch -- it must not fail the gate."""
    _write_schema(tmp_path / "pokemon_asset.schema.json", ["pokemon_asset_key"])

    checks = report.build_schema_drift_checks(tmp_path)

    assert checks == [
        {
            "table_name": "pokemon_asset",
            "status": "skipped",
            "expected_fields": ["pokemon_asset_key"],
            "actual_fields": None,
        }
    ]


def test_build_report_folds_schema_drift_failures_into_release_blocking_findings(tmp_path):
    _write_schema(tmp_path / "pokemon.schema.json", ["pokemon_key", "pokemon_name"])
    _write_csv(tmp_path / "pokemon.csv", ["pokemon_key", "species_name"])

    result = report.build_report(
        {"nodes": {}},
        {"results": []},
        dataset_version="0.1.0",
        warehouse_path=None,
        normalized_dir=tmp_path,
    )

    assert result["schema_drift_checks"][0]["status"] == "fail"
    assert "pokemon: status=fail" in result["release_blocking_findings"]


def test_build_report_categorizes_mart_quality_checks():
    manifest = {
        "nodes": {
            "test.pokemon_champions.not_null_pokemon_usage_summary_pokemon_key.abc123": (
                _manifest_node(
                    "not_null_pokemon_usage_summary_pokemon_key",
                    {"category": "mart_quality", "table_name": "pokemon_usage_summary"},
                )
            ),
        }
    }
    run_results = {
        "results": [
            _run_result(
                "test.pokemon_champions.not_null_pokemon_usage_summary_pokemon_key.abc123",
                "fail",
                3,
            ),
        ]
    }

    result = report.build_report(
        manifest, run_results, dataset_version="0.1.0", warehouse_path=None
    )
    template = _template()

    assert set(result) == set(template)
    assert result["mart_quality_checks"] == [
        {
            "table_name": "pokemon_usage_summary",
            "check_name": "not_null_pokemon_usage_summary_pokemon_key",
            "status": "fail",
            "failures": 3,
        }
    ]


def test_build_report_never_folds_mart_quality_into_release_blocking_findings():
    """Marts branch off the normalized layer for dashboard-facing output
    and aren't part of the release package (CLAUDE.md's "Repository
    structure"), so a failing mart_quality check must stay visible in the
    report without blocking pipelines.cli release -- unlike every other
    category, which does block (backlog.md #42)."""
    manifest = {
        "nodes": {
            "test.pokemon_champions.unique_pokemon_speed_tiers_pokemon_key.def456": (
                _manifest_node(
                    "unique_pokemon_speed_tiers_pokemon_key",
                    {"category": "mart_quality", "table_name": "pokemon_speed_tiers"},
                )
            ),
        }
    }
    run_results = {
        "results": [
            _run_result(
                "test.pokemon_champions.unique_pokemon_speed_tiers_pokemon_key.def456",
                "fail",
                2,
            ),
        ]
    }

    result = report.build_report(
        manifest, run_results, dataset_version="0.1.0", warehouse_path=None
    )

    assert result["mart_quality_checks"][0]["status"] == "fail"
    assert result["release_blocking_findings"] == []


def test_build_report_categorizes_archetype_drift_checks():
    manifest = {
        "nodes": {
            "test.pokemon_champions.assert_archetype_pokemon_map_intra_group_synergy.abc123": (
                _manifest_node(
                    "assert_archetype_pokemon_map_intra_group_synergy",
                    {
                        "category": "archetype_drift",
                        "check_name": "archetype_pokemon_map_intra_group_synergy",
                    },
                )
            ),
        }
    }
    run_results = {
        "results": [
            _run_result(
                "test.pokemon_champions.assert_archetype_pokemon_map_intra_group_synergy.abc123",
                "warn",
                3,
            ),
        ]
    }

    result = report.build_report(
        manifest, run_results, dataset_version="0.1.0", warehouse_path=None
    )
    template = _template()

    assert set(result) == set(template)
    assert result["archetype_drift_checks"] == [
        {
            "check_name": "archetype_pokemon_map_intra_group_synergy",
            "status": "warn",
            "flagged_archetype_count": 3,
        }
    ]


def test_build_report_never_folds_archetype_drift_into_release_blocking_findings():
    """archetype_drift's own dbt test uses severity=warn, so its status
    can never be "fail" -- but the category is also explicitly excluded
    here as documented intent, not left to rely on that alone
    (backlog.md #15)."""
    manifest = {
        "nodes": {
            "test.pokemon_champions.assert_archetype_pokemon_map_intra_group_synergy.abc123": (
                _manifest_node(
                    "assert_archetype_pokemon_map_intra_group_synergy",
                    {
                        "category": "archetype_drift",
                        "check_name": "archetype_pokemon_map_intra_group_synergy",
                    },
                )
            ),
        }
    }
    run_results = {
        "results": [
            _run_result(
                "test.pokemon_champions.assert_archetype_pokemon_map_intra_group_synergy.abc123",
                "warn",
                3,
            ),
        ]
    }

    result = report.build_report(
        manifest, run_results, dataset_version="0.1.0", warehouse_path=None
    )

    assert result["release_blocking_findings"] == []


def test_build_report_routes_unrecognized_test_to_uncategorized():
    """A test with no meta.category (e.g. a newly-added test nobody tagged
    yet) must still surface and be able to block a release -- it must not
    silently vanish from the report the way five real tests once did
    (docs/backlog.md #37)."""
    manifest = {
        "nodes": {
            "test.pokemon_champions.assert_something_new.abc123": _manifest_node(
                "assert_something_new"
            ),
        }
    }
    run_results = {
        "results": [
            _run_result("test.pokemon_champions.assert_something_new.abc123", "fail", 3),
        ]
    }

    result = report.build_report(
        manifest, run_results, dataset_version="0.1.0", warehouse_path=None
    )

    assert result["uncategorized_checks"] == [
        {"test_name": "assert_something_new", "status": "fail", "failures": 3}
    ]
    assert "assert_something_new: status=fail" in result["release_blocking_findings"]


def test_recompute_bps_ratio_recovers_true_value_on_a_passing_check(tmp_path):
    """Backlog #49: dbt-core hardcodes `failures = 0` for a *passing* test
    (dbt/task/test.py's TestRunner.build_test_run_result) regardless of the
    test's real fail_calc value, so `result["failures"]` can't be trusted
    on the pass path. Re-executing the test's own compiled_code against the
    warehouse (wrapped in its own fail_calc expression, exactly like dbt
    itself would) must recover the true ratio even though this result's
    `failures`/status claim the check passed with 0 failures."""
    warehouse_path = tmp_path / "warehouse.duckdb"
    con = duckdb.connect(str(warehouse_path))
    con.execute("create table t as select * from (values (1), (0), (1), (1)) as v(n)")
    con.close()

    node = {"config": {"fail_calc": "max(pass_bps)"}}
    result = {
        "status": "pass",
        "failures": 0,
        "compiled_code": (
            "select round(sum(n)::double / count(*) * 10000)::integer as pass_bps from t"
        ),
    }

    assert report._recompute_bps_ratio(node, result, warehouse_path) == 0.75


def test_recompute_bps_ratio_falls_back_when_warehouse_missing(tmp_path):
    node = {"config": {"fail_calc": "max(pass_bps)"}}
    result = {"status": "pass", "failures": 0, "compiled_code": "select 1 as pass_bps"}

    assert report._recompute_bps_ratio(node, result, tmp_path / "no_such.duckdb") == 0.0


def test_recompute_bps_ratio_falls_back_when_node_declares_no_fail_calc(tmp_path):
    warehouse_path = tmp_path / "warehouse.duckdb"
    duckdb.connect(str(warehouse_path)).close()

    node = {"config": {}}
    result = {"status": "fail", "failures": 300}

    assert report._recompute_bps_ratio(node, result, warehouse_path) == 0.03


def test_recompute_bps_ratio_falls_back_on_a_broken_compiled_query(tmp_path):
    """The recompute query itself can fail (e.g. a stale run_results.json
    pointing at a relation the current warehouse no longer has) -- that
    must degrade to the pre-#49 `_ratio_from_bps(result)` fallback, not
    raise out of report generation."""
    warehouse_path = tmp_path / "warehouse.duckdb"
    duckdb.connect(str(warehouse_path)).close()

    node = {"config": {"fail_calc": "max(pass_bps)"}}
    result = {
        "status": "pass",
        "failures": 0,
        "compiled_code": "select * from no_such_table",
    }

    assert report._recompute_bps_ratio(node, result, warehouse_path) == 0.0


def test_recompute_bps_ratio_resolves_relative_source_paths_from_the_dbt_project_dir(tmp_path):
    """dbt-duckdb inlines a `source()` reference as a literal, relative CSV
    glob path in compiled_code (e.g. `'../data/staging/x/*.csv'`), resolved
    against dbt's own working directory at query time -- not the repo root,
    and not wherever this process happens to be running from. Confirmed
    against a real build (see docs/backlog.md #49) that the naive "just
    connect and run it" approach silently reads zero rows instead of
    erroring, which is why this needs its own regression test rather than
    trusting the happy-path fixture above."""
    dbt_dir = tmp_path / "dbt"
    (dbt_dir / "data").mkdir(parents=True)
    staging_dir = tmp_path / "data" / "staging" / "widget"
    staging_dir.mkdir(parents=True)
    (staging_dir / "2026-01-01.csv").write_text("legal\ntrue\ntrue\nfalse\n")

    warehouse_path = dbt_dir / "data" / "warehouse.duckdb"
    duckdb.connect(str(warehouse_path)).close()

    node = {"config": {"fail_calc": "max(legal_bps)"}}
    result = {
        "status": "pass",
        "failures": 0,
        "compiled_code": (
            "select round(sum(case when legal then 1 else 0 end)::double "
            "/ count(*) * 10000)::integer as legal_bps "
            "from '../data/staging/widget/*.csv'"
        ),
    }

    assert report._recompute_bps_ratio(node, result, warehouse_path) == pytest.approx(
        0.6667, abs=1e-4
    )
