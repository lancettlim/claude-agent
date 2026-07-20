"""Reshape dbt test results into reports/validation/validation_report.json.

The gates in docs/dataset-spec.md ("Validation and release gates") are
implemented as dbt singular tests under dbt/tests/singular/ (see that
directory's tests for the actual SQL). This module reads dbt's own
target/manifest.json and target/run_results.json after a `dbt build` (or
`dbt test`) run and reshapes those results into the project-specific report
shape defined by reports/validation/validation_report.template.json.

Matching a singular test's result back to a report entry is done via the
test's `name` (the file stem, e.g. "assert_duplicate_key_pokemon"), which
dbt keeps stable and human-readable — unlike a test's `unique_id`, which may
carry a hash suffix. `name` -> `unique_id` comes from manifest.json;
`unique_id` -> pass/fail/failure-count comes from run_results.json.

Null-rate and coverage checks need an actual ratio (not just a failing-row
count) in `metric_value`. dbt's run_results.json schema requires `failures`
to be an integer, so those singular tests can't report a raw ratio directly
(a fractional `fail_calc` result crashes dbt's results serialization) —
instead they report the ratio in basis points (1.0 == 10000 bps) via a
`fail_calc` override (e.g. `fail_calc = "max(null_rate_bps)"`), and
`_ratio_from_bps` below divides back down to a ratio for `metric_value`.
Duplicate-key and referential-integrity checks use dbt's default
`fail_calc` (`count(*)`), so `failures` is already the duplicate/violation
count the report wants.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DBT_TARGET_DIR = REPO_ROOT / "dbt" / "target"
REPORT_PATH = REPO_ROOT / "reports" / "validation" / "validation_report.json"

# table_name -> (primary_key, singular test file stem)
DUPLICATE_KEY_TABLES: dict[str, tuple[str, str]] = {
    "pokemon": ("pokemon_key", "assert_duplicate_key_pokemon"),
    "pokemon_stat_canonical": (
        "pokemon_stat_canonical_key",
        "assert_duplicate_key_pokemon_stat_canonical",
    ),
    "pokemon_stat_champions": (
        "pokemon_stat_champions_key",
        "assert_duplicate_key_pokemon_stat_champions",
    ),
    "pokemon_stat_delta": ("pokemon_stat_delta_key", "assert_duplicate_key_pokemon_stat_delta"),
    "legality_snapshot": ("legality_snapshot_key", "assert_duplicate_key_legality_snapshot"),
    "tournament_event": ("event_id", "assert_duplicate_key_tournament_event"),
    "tournament_team": ("team_id", "assert_duplicate_key_tournament_team"),
    "tournament_team_member": ("team_member_id", "assert_duplicate_key_tournament_team_member"),
    "pokemon_asset": ("pokemon_asset_key", "assert_duplicate_key_pokemon_asset"),
}

# table_name -> singular test file stem
NULL_RATE_TABLES: dict[str, str] = {
    "pokemon": "assert_null_rate_pokemon",
    "pokemon_stat_canonical": "assert_null_rate_pokemon_stat_canonical",
    "pokemon_stat_champions": "assert_null_rate_pokemon_stat_champions",
    "pokemon_stat_delta": "assert_null_rate_pokemon_stat_delta",
    "legality_snapshot": "assert_null_rate_legality_snapshot",
    "tournament_event": "assert_null_rate_tournament_event",
    "tournament_team": "assert_null_rate_tournament_team",
    "tournament_team_member": "assert_null_rate_tournament_team_member",
    "pokemon_asset": "assert_null_rate_pokemon_asset",
}

# check_name (matches validation_report.template.json exactly) -> singular test file stem
REFERENTIAL_INTEGRITY_CHECKS: dict[str, str] = {
    "pokemon_stat_canonical_resolves_to_pokemon": "assert_pokemon_stat_canonical_resolves_to_pokemon",
    "pokemon_stat_champions_resolves_to_pokemon": "assert_pokemon_stat_champions_resolves_to_pokemon",
    "pokemon_stat_delta_resolves_to_pokemon": "assert_pokemon_stat_delta_resolves_to_pokemon",
    "legality_snapshot_resolves_to_pokemon": "assert_legality_snapshot_resolves_to_pokemon",
    "tournament_team_resolves_to_tournament_event": "assert_tournament_team_resolves_to_tournament_event",
    "tournament_team_member_resolves_to_tournament_team": "assert_tournament_team_member_resolves_to_tournament_team",
    "tournament_team_member_resolves_to_pokemon": "assert_tournament_team_member_resolves_to_pokemon",
    "pokemon_asset_resolves_to_pokemon": "assert_pokemon_asset_resolves_to_pokemon",
}

# check_name -> (threshold, description, singular test file stem)
COVERAGE_CHECKS: dict[str, tuple[str, str, str]] = {
    "opgg_legal_pool_coverage": (
        ">=0.95",
        "Share of OP.GG legal pool rows mapped to a canonical pokemon_id",
        "assert_opgg_legal_pool_coverage",
    ),
    "tournament_team_member_mapping_coverage": (
        ">=0.90",
        "Share of tournament roster rows mapped to normalized team tables",
        "assert_tournament_team_member_mapping_coverage",
    ),
    "pokebase_legal_pool_coverage": (
        ">=0.95",
        "Share of PokéBase legal-pool rows mapped to a canonical pokemon_id",
        "assert_pokebase_legal_pool_coverage",
    ),
    "bulbagarden_sprite_coverage": (
        ">=0.85",
        "Share of Bulbagarden sprite titles mapped to pokemon_asset rows",
        "assert_bulbagarden_sprite_coverage",
    ),
}


class DbtArtifactsMissing(RuntimeError):
    """Raised when dbt's target/ artifacts are absent (dbt build hasn't run)."""


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise DbtArtifactsMissing(
            f"{path} not found — run `dbt build` (e.g. `make dbt-build`) before validating"
        )
    return json.loads(path.read_text())


def _test_name_to_result(
    manifest: dict[str, Any], run_results: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    """Map each test's stable `name` to its run_results.json result entry."""
    name_to_unique_id = {
        node["name"]: unique_id
        for unique_id, node in manifest["nodes"].items()
        if node["resource_type"] == "test"
    }
    result_by_unique_id = {result["unique_id"]: result for result in run_results["results"]}
    return {
        name: result_by_unique_id[unique_id]
        for name, unique_id in name_to_unique_id.items()
        if unique_id in result_by_unique_id
    }


def _ratio_from_bps(result: dict[str, Any] | None) -> float | None:
    """Recover a 0-1 ratio from a fail_calc result reported in basis points."""
    if result is None or result["failures"] is None:
        return None
    return result["failures"] / 10000.0


def _status_for(result: dict[str, Any] | None) -> str:
    if result is None:
        return "skipped"
    if result["status"] == "pass":
        return "pass"
    if result["status"] in ("fail", "error"):
        return "fail"
    return result["status"]  # "warn" or "skipped"


def build_report(
    manifest: dict[str, Any],
    run_results: dict[str, Any],
    dataset_version: str,
) -> dict[str, Any]:
    """Build a dict matching reports/validation/validation_report.template.json's shape."""
    results_by_name = _test_name_to_result(manifest, run_results)

    coverage_checks = []
    for check_name, (threshold, description, test_name) in COVERAGE_CHECKS.items():
        result = results_by_name.get(test_name)
        coverage_checks.append(
            {
                "check_name": check_name,
                "description": description,
                "threshold": threshold,
                "metric_value": _ratio_from_bps(result),
                "status": _status_for(result),
            }
        )

    null_rate_checks = []
    for table_name, test_name in NULL_RATE_TABLES.items():
        result = results_by_name.get(test_name)
        null_rate_checks.append(
            {
                "table_name": table_name,
                "metric_value": _ratio_from_bps(result),
                "threshold": "<=0.01",
                "status": _status_for(result),
            }
        )

    duplicate_key_checks = []
    for table_name, (primary_key, test_name) in DUPLICATE_KEY_TABLES.items():
        result = results_by_name.get(test_name)
        duplicate_key_checks.append(
            {
                "table_name": table_name,
                "primary_key": primary_key,
                "duplicate_count": result["failures"] if result else None,
                "status": _status_for(result),
            }
        )

    referential_integrity_checks = []
    for check_name, test_name in REFERENTIAL_INTEGRITY_CHECKS.items():
        result = results_by_name.get(test_name)
        referential_integrity_checks.append(
            {
                "check_name": check_name,
                "status": _status_for(result),
                "violation_count": result["failures"] if result else None,
            }
        )

    release_blocking_findings = [
        f"{entry.get('table_name') or entry.get('check_name')}: status={entry['status']}"
        for entry in (
            *coverage_checks,
            *null_rate_checks,
            *duplicate_key_checks,
            *referential_integrity_checks,
        )
        if entry["status"] == "fail"
    ]

    return {
        "dataset_version": dataset_version,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "coverage_checks": coverage_checks,
        "null_rate_checks": null_rate_checks,
        "duplicate_key_checks": duplicate_key_checks,
        "referential_integrity_checks": referential_integrity_checks,
        "release_blocking_findings": release_blocking_findings,
    }


def write_report(report: dict[str, Any], path: Path = REPORT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n")


def generate(dataset_version: str = "0.1.0", target_dir: Path = DBT_TARGET_DIR) -> dict[str, Any]:
    """Load dbt's artifacts from a completed `dbt build`/`dbt test` run and
    write reports/validation/validation_report.json."""
    manifest = _load_json(target_dir / "manifest.json")
    run_results = _load_json(target_dir / "run_results.json")
    report = build_report(manifest, run_results, dataset_version)
    write_report(report)
    return report
