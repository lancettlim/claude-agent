import json

from pipelines.validate import report


def _manifest_node(name: str) -> dict:
    return {"resource_type": "test", "name": name}


def _run_result(unique_id: str, status: str, failures) -> dict:
    return {"unique_id": unique_id, "status": status, "failures": failures}


def _template() -> dict:
    path = report.REPO_ROOT / "reports" / "validation" / "validation_report.template.json"
    return json.loads(path.read_text())


def test_build_report_matches_template_shape():
    manifest = {
        "nodes": {
            "test.pokemon_champions.assert_duplicate_key_pokemon.abc123": _manifest_node(
                "assert_duplicate_key_pokemon"
            ),
            "test.pokemon_champions.assert_null_rate_pokemon.def456": _manifest_node(
                "assert_null_rate_pokemon"
            ),
            "test.pokemon_champions.assert_pokemon_stat_canonical_resolves_to_pokemon.ghi789": (
                _manifest_node("assert_pokemon_stat_canonical_resolves_to_pokemon")
            ),
            "test.pokemon_champions.assert_opgg_legal_pool_coverage.jkl012": _manifest_node(
                "assert_opgg_legal_pool_coverage"
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

    result = report.build_report(manifest, run_results, dataset_version="0.1.0")
    template = _template()

    assert set(result) == set(template)

    assert {c["table_name"] for c in result["duplicate_key_checks"]} == {
        c["table_name"] for c in template["duplicate_key_checks"]
    }
    assert {c["table_name"] for c in result["null_rate_checks"]} == {
        c["table_name"] for c in template["null_rate_checks"]
    }
    assert {c["check_name"] for c in result["referential_integrity_checks"]} == {
        c["check_name"] for c in template["referential_integrity_checks"]
    }
    assert {c["check_name"] for c in result["coverage_checks"]} == {
        c["check_name"] for c in template["coverage_checks"]
    }

    pokemon_dup_check = next(
        c for c in result["duplicate_key_checks"] if c["table_name"] == "pokemon"
    )
    assert pokemon_dup_check["status"] == "pass"
    assert pokemon_dup_check["duplicate_count"] == 0

    pokemon_null_check = next(c for c in result["null_rate_checks"] if c["table_name"] == "pokemon")
    assert pokemon_null_check["status"] == "fail"
    assert pokemon_null_check["metric_value"] == 0.02

    opgg_coverage_check = next(
        c for c in result["coverage_checks"] if c["check_name"] == "opgg_legal_pool_coverage"
    )
    assert opgg_coverage_check["metric_value"] == 1.0

    assert "pokemon: status=fail" in result["release_blocking_findings"]


def test_build_report_marks_missing_tests_as_skipped():
    result = report.build_report({"nodes": {}}, {"results": []}, dataset_version="0.1.0")

    assert all(c["status"] == "skipped" for c in result["duplicate_key_checks"])
    assert all(c["duplicate_count"] is None for c in result["duplicate_key_checks"])
    assert all(c["metric_value"] is None for c in result["null_rate_checks"])
    assert all(c["metric_value"] is None for c in result["coverage_checks"])
    assert all(c["violation_count"] is None for c in result["referential_integrity_checks"])
    assert result["release_blocking_findings"] == []
