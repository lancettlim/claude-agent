"""Reshape dbt test results into reports/validation/validation_report.json.

The gates in docs/dataset-spec.md ("Validation and release gates") are
implemented as dbt singular tests under dbt/tests/singular/ (see that
directory's tests for the actual SQL). This module reads dbt's own
target/manifest.json and target/run_results.json after a `dbt build` (or
`dbt test`) run and reshapes those results into the project-specific report
shape defined by reports/validation/validation_report.template.json.

Which report section a test belongs in, and the fields that section needs
(table_name/primary_key, check_name/description/threshold, ...), is read
from each test's own `meta` config (a `{{ config(meta={...}) }}` Jinja call
in the test's .sql file — see dbt/tests/singular/*.sql), not from a
hardcoded name -> section mapping kept here. This closes backlog #37's gap:
previously, a new singular test was invisible to the release gate until
someone remembered to add it to one of four dicts in this file (as actually
happened to five real tests — see docs/backlog.md #37). Now a test just
declares its own `meta.category`; any test that runs but declares no
recognized category lands in `uncategorized_checks` instead of disappearing,
so a failing test can never silently skip blocking a release.

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

from pipelines.versioning import latest_published_version

REPO_ROOT = Path(__file__).resolve().parents[2]
DBT_TARGET_DIR = REPO_ROOT / "dbt" / "target"
REPORT_PATH = REPO_ROOT / "reports" / "validation" / "validation_report.json"


class DbtArtifactsMissing(RuntimeError):
    """Raised when dbt's target/ artifacts are absent (dbt build hasn't run)."""


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise DbtArtifactsMissing(
            f"{path} not found — run `dbt build` (e.g. `make dbt-build`) before validating"
        )
    return json.loads(path.read_text())


def _test_nodes_with_results(
    manifest: dict[str, Any], run_results: dict[str, Any]
) -> list[tuple[dict[str, Any], dict[str, Any] | None]]:
    """Pair each test node in the manifest with its run_results.json result.

    A test with no matching run_results entry (e.g. dbt build was interrupted
    before it ran) is paired with `None` rather than dropped, so it still
    surfaces as "skipped" instead of vanishing.
    """
    result_by_unique_id = {result["unique_id"]: result for result in run_results["results"]}
    return [
        (node, result_by_unique_id.get(unique_id))
        for unique_id, node in manifest["nodes"].items()
        if node["resource_type"] == "test"
    ]


def _freshness_status(dbt_status: str) -> str:
    """Map dbt source-freshness's own status vocabulary onto this report's
    pass/warn/fail/skipped vocabulary. "error" (past error_after) and
    "runtime error" (the freshness query itself failed) both block a
    release -- an unmeasurable freshness is treated the same as a stale
    one, not silently passed."""
    if dbt_status in ("error", "runtime error"):
        return "fail"
    if dbt_status in ("pass", "warn"):
        return dbt_status
    return dbt_status


def build_freshness_checks(sources_result: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Reshape `dbt source freshness`'s target/sources.json into this
    report's freshness_checks list (backlog.md #39). `sources_result` is
    None when freshness wasn't run at all (e.g. an older dbt, or a caller
    that only ran `dbt build`) -- that degrades to an empty list rather
    than raising, since freshness is an additional gate layered on top of
    the existing build/test gates, not a replacement for them.
    """
    if not sources_result:
        return []
    checks = []
    for result in sources_result.get("results", []):
        source_name = result["unique_id"].rsplit(".", 1)[-1]
        checks.append(
            {
                "source_name": source_name,
                "status": _freshness_status(result["status"]),
                "max_loaded_at": result.get("max_loaded_at"),
                "age_hours": (
                    round(result["max_loaded_at_time_ago_in_s"] / 3600, 1)
                    if result.get("max_loaded_at_time_ago_in_s") is not None
                    else None
                ),
            }
        )
    checks.sort(key=lambda c: c["source_name"])
    return checks


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
    sources_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a dict matching reports/validation/validation_report.template.json's shape.

    Every singular test in the manifest is categorized by its own
    `config.meta.category` (see this module's docstring) rather than a
    hardcoded test-name lookup, so a new test is gated as soon as it declares
    a category — nothing needs editing here. A test with no `meta.category`,
    or one this module doesn't recognize, lands in `uncategorized_checks`
    instead of being silently dropped from the report.

    `sources_result` is the parsed target/sources.json from a `dbt source
    freshness` run (backlog.md #39); omit it (or pass None) if that command
    wasn't run, and freshness_checks is simply empty.
    """
    freshness_checks = build_freshness_checks(sources_result)
    coverage_checks = []
    null_rate_checks = []
    duplicate_key_checks = []
    referential_integrity_checks = []
    uncategorized_checks = []

    for node, result in _test_nodes_with_results(manifest, run_results):
        meta = node.get("config", {}).get("meta", {}) or {}
        category = meta.get("category")
        status = _status_for(result)

        if category == "coverage" and "check_name" in meta:
            coverage_checks.append(
                {
                    "check_name": meta["check_name"],
                    "description": meta.get("description"),
                    "threshold": meta.get("threshold"),
                    "metric_value": _ratio_from_bps(result),
                    "status": status,
                }
            )
        elif category == "null_rate" and "table_name" in meta:
            null_rate_checks.append(
                {
                    "table_name": meta["table_name"],
                    "metric_value": _ratio_from_bps(result),
                    "threshold": "<=0.01",
                    "status": status,
                }
            )
        elif category == "duplicate_key" and "table_name" in meta:
            duplicate_key_checks.append(
                {
                    "table_name": meta["table_name"],
                    "primary_key": meta.get("primary_key"),
                    "duplicate_count": result["failures"] if result else None,
                    "status": status,
                }
            )
        elif category == "referential_integrity" and "check_name" in meta:
            referential_integrity_checks.append(
                {
                    "check_name": meta["check_name"],
                    "status": status,
                    "violation_count": result["failures"] if result else None,
                }
            )
        else:
            uncategorized_checks.append(
                {
                    "test_name": node["name"],
                    "status": status,
                    "failures": result["failures"] if result else None,
                }
            )

    coverage_checks.sort(key=lambda c: c["check_name"])
    null_rate_checks.sort(key=lambda c: c["table_name"])
    duplicate_key_checks.sort(key=lambda c: c["table_name"])
    referential_integrity_checks.sort(key=lambda c: c["check_name"])
    uncategorized_checks.sort(key=lambda c: c["test_name"])

    release_blocking_findings = [
        f"{entry.get('table_name') or entry.get('check_name') or entry.get('test_name') or entry.get('source_name')}: "
        f"status={entry['status']}"
        for entry in (
            *coverage_checks,
            *null_rate_checks,
            *duplicate_key_checks,
            *referential_integrity_checks,
            *uncategorized_checks,
            *freshness_checks,
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
        "uncategorized_checks": uncategorized_checks,
        "freshness_checks": freshness_checks,
        "release_blocking_findings": release_blocking_findings,
    }


def write_report(report: dict[str, Any], path: Path = REPORT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n")


def generate(
    dataset_version: str | None = None, target_dir: Path = DBT_TARGET_DIR
) -> dict[str, Any]:
    """Load dbt's artifacts from a completed `dbt build`/`dbt test` run and
    write reports/validation/validation_report.json.

    `dataset_version` defaults to the latest published version (see
    pipelines/versioning.py) rather than a hardcoded placeholder, so the
    report reflects reality even as new versions are published.

    target/sources.json (written by a separate `dbt source freshness` run --
    not part of `dbt build`) is read if present; its absence doesn't raise,
    since freshness is an additional gate layered on the existing ones, not
    a hard prerequisite for every caller of this function.
    """
    if dataset_version is None:
        dataset_version = latest_published_version()
    manifest = _load_json(target_dir / "manifest.json")
    run_results = _load_json(target_dir / "run_results.json")
    sources_path = target_dir / "sources.json"
    sources_result = json.loads(sources_path.read_text()) if sources_path.exists() else None
    report = build_report(manifest, run_results, dataset_version, sources_result)
    write_report(report)
    return report
