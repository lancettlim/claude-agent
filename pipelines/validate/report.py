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
so a failing test can never silently skip blocking a release. The
deliberate exceptions are `mart_quality` (backlog.md #42) and
`archetype_drift` (backlog.md #15): those checks are real and reported,
but never fold into `release_blocking_findings` -- marts branch off the
normalized layer for dashboard-facing output and aren't part of the
release package (CLAUDE.md's "Repository structure"), and archetype drift
is softer still, flagging a curated seed's mismatch against real data as
signal worth seeing, not a defect that should block
`pipelines.cli release`.

Null-rate and coverage checks need an actual ratio (not just a failing-row
count) in `metric_value`. dbt's run_results.json schema requires `failures`
to be an integer, so those singular tests can't report a raw ratio directly
(a fractional `fail_calc` result crashes dbt's results serialization) —
instead they report the ratio in basis points (1.0 == 10000 bps) via a
`fail_calc` override (e.g. `fail_calc = "max(null_rate_bps)"`).
Duplicate-key and referential-integrity checks use dbt's default
`fail_calc` (`count(*)`), so `failures` is already the duplicate/violation
count the report wants.

Backlog #49: dbt-core's `TestRunner.build_test_run_result`
(`dbt/task/test.py`) hardcodes `failures = 0` on a *passing* test and only
assigns the real `fail_calc` value on the fail/warn branches — so
`run_results.json["failures"]` is only trustworthy for a bps-based check
when it fails, not when it passes. `_recompute_bps_ratio` below works
around that by re-executing the test's own compiled SQL (each
`run_results.json` result already carries `compiled_code`, the fully
ref/source-resolved query dbt just ran) against the built warehouse,
wrapped in the same `fail_calc` expression the manifest already declares
(`node.config.fail_calc`) — recovering the true ratio regardless of
pass/fail, deterministically, since the underlying data hasn't changed
since dbt itself ran that query moments earlier. `_ratio_from_bps` is kept
as the fallback for when the warehouse file isn't available (e.g. a caller
that only has archived run_results.json/manifest.json, not the .duckdb
file itself) — correct on the fail path, and the best available answer on
the pass path (still better than crashing).
"""

from __future__ import annotations

import contextlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

from pipelines.schema_contracts import csv_header, schema_field_names
from pipelines.versioning import latest_published_version

REPO_ROOT = Path(__file__).resolve().parents[2]
DBT_TARGET_DIR = REPO_ROOT / "dbt" / "target"
DBT_WAREHOUSE_PATH = REPO_ROOT / "dbt" / "data" / "warehouse.duckdb"
REPORT_PATH = REPO_ROOT / "reports" / "validation" / "validation_report.json"
NORMALIZED_DIR = REPO_ROOT / "data" / "normalized"


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


def build_schema_drift_checks(normalized_dir: Path = NORMALIZED_DIR) -> list[dict[str, Any]]:
    """Compare each data/normalized/<entity>.csv's actual header against
    its data/normalized/<entity>.schema.json contract (backlog.md #41) --
    the normalized-layer half of schema-drift enforcement (the staging
    half, extractor FIELDNAMES vs data/staging/*.schema.json, is a pure
    code-level check covered directly by
    tests/unit/extract/test_schema_contracts.py, no build needed).

    One entry per data/normalized/*.schema.json file found, regardless of
    whether the matching .csv exists yet -- a missing CSV (e.g. a fresh
    clone with no `dbt build` yet, or pokemon_asset before Bulbagarden has
    ever been extracted) reports "skipped", not "fail": there's no drift
    to detect against data that was never produced, and that's a
    different case from a real mismatch.
    """
    checks = []
    for schema_path in sorted(normalized_dir.glob("*.schema.json")):
        entity = schema_path.name[: -len(".schema.json")]
        csv_path = normalized_dir / f"{entity}.csv"
        expected_fields = schema_field_names(schema_path)
        if not csv_path.exists():
            checks.append(
                {
                    "table_name": entity,
                    "status": "skipped",
                    "expected_fields": expected_fields,
                    "actual_fields": None,
                }
            )
            continue
        actual_fields = csv_header(csv_path)
        checks.append(
            {
                "table_name": entity,
                "status": "pass" if actual_fields == expected_fields else "fail",
                "expected_fields": expected_fields,
                "actual_fields": actual_fields,
            }
        )
    return checks


def _ratio_from_bps(result: dict[str, Any] | None) -> float | None:
    """Recover a 0-1 ratio from a fail_calc result reported in basis points.

    Only trustworthy when the check failed or warned -- see this module's
    docstring and `_recompute_bps_ratio` for why a passing check's
    `failures` can't be trusted at all (backlog #49).
    """
    if result is None or result["failures"] is None:
        return None
    return result["failures"] / 10000.0


@contextlib.contextmanager
def _chdir(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def _recompute_bps_ratio(
    node: dict[str, Any],
    result: dict[str, Any] | None,
    warehouse_path: Path | None,
) -> float | None:
    """Recover a bps-based check's true 0-1 ratio regardless of pass/fail
    status, by re-executing its own compiled SQL against the built
    warehouse (backlog #49 -- see this module's docstring for why
    `result["failures"]` alone can't be trusted on the passing path).

    A test's compiled SQL isn't self-contained: dbt-duckdb inlines a
    `source()` reference to an external table as a literal, relative CSV
    glob path (e.g. `'../data/staging/opgg_champions/*.csv'`), resolved
    relative to dbt's own working directory (the `dbt/` project dir) at
    query time -- unlike a `ref()`, which compiles to a real
    already-materialized relation name, valid from any cwd. So this
    temporarily chdirs into the warehouse's parent `dbt/` project directory
    for the duration of the recompute query, confirmed necessary by testing
    directly against a real build: the same query returns the correct ratio
    from `dbt/` and a wrong one (relative paths resolving against the
    wrong base and silently reading zero rows) from the repo root.

    Falls back to `_ratio_from_bps(result)` whenever the recompute isn't
    possible (no warehouse file, no compiled_code/fail_calc on this node, or
    the recompute query itself errors) rather than raising -- report
    generation should degrade to the pre-#49 behavior, not fail outright.
    """
    fallback = _ratio_from_bps(result)
    if result is None:
        return fallback
    fail_calc = node.get("config", {}).get("fail_calc")
    compiled_code = result.get("compiled_code")
    if not fail_calc or not compiled_code or warehouse_path is None or not warehouse_path.exists():
        return fallback
    try:
        with _chdir(warehouse_path.parent.parent):
            con = duckdb.connect(str(warehouse_path), read_only=True)
            try:
                value = con.execute(
                    f"select {fail_calc} as value from ({compiled_code}) as _bps_recompute"
                ).fetchone()[0]
            finally:
                con.close()
    except duckdb.Error:
        return fallback
    return fallback if value is None else value / 10000.0


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
    warehouse_path: Path | None = DBT_WAREHOUSE_PATH,
    normalized_dir: Path = NORMALIZED_DIR,
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

    `warehouse_path` points at the built DuckDB warehouse file, used to
    recompute bps-based (coverage/null_rate/row_count_anomaly) metric values
    that dbt itself only reports correctly on the failing path (backlog
    #49); pass None to skip the recompute and fall back to
    `_ratio_from_bps` unconditionally (e.g. in a test with no real
    warehouse to point at).

    `normalized_dir` points at data/normalized/, used for the
    schema_drift_checks section (backlog.md #41): each *.schema.json
    contract's declared fields compared against the matching *.csv's
    actual header, catching a column rename/add/drop that a bare
    `select *` staging model would otherwise pass through silently.
    """
    freshness_checks = build_freshness_checks(sources_result)
    schema_drift_checks = build_schema_drift_checks(normalized_dir)
    coverage_checks = []
    null_rate_checks = []
    duplicate_key_checks = []
    referential_integrity_checks = []
    row_count_anomaly_checks = []
    mart_quality_checks = []
    archetype_drift_checks = []
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
                    "metric_value": _recompute_bps_ratio(node, result, warehouse_path),
                    "status": status,
                }
            )
        elif category == "null_rate" and "table_name" in meta:
            null_rate_checks.append(
                {
                    "table_name": meta["table_name"],
                    "metric_value": _recompute_bps_ratio(node, result, warehouse_path),
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
        elif category == "row_count_anomaly" and "source_name" in meta:
            row_count_anomaly_checks.append(
                {
                    "source_name": meta["source_name"],
                    "metric_value": _recompute_bps_ratio(node, result, warehouse_path),
                    "threshold": ">=0.5x previous snapshot",
                    "status": status,
                }
            )
        elif category == "mart_quality" and "table_name" in meta:
            mart_quality_checks.append(
                {
                    "table_name": meta["table_name"],
                    "check_name": node["name"],
                    "status": status,
                    "failures": result["failures"] if result else None,
                }
            )
        elif category == "archetype_drift" and "check_name" in meta:
            archetype_drift_checks.append(
                {
                    "check_name": meta["check_name"],
                    "status": status,
                    "flagged_archetype_count": result["failures"] if result else None,
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
    row_count_anomaly_checks.sort(key=lambda c: c["source_name"])
    mart_quality_checks.sort(key=lambda c: (c["table_name"], c["check_name"]))
    archetype_drift_checks.sort(key=lambda c: c["check_name"])
    uncategorized_checks.sort(key=lambda c: c["test_name"])

    # mart_quality_checks (backlog.md #42) and archetype_drift_checks
    # (backlog.md #15) are both deliberately excluded here. Marts branch
    # off the normalized layer for dashboard-facing output and aren't part
    # of the release package (CLAUDE.md's "Repository structure"), so a
    # mart-quality failure should be visible without blocking
    # `pipelines.cli release`. archetype_drift_checks is even softer: it
    # flags when the curated, NOT-sourced archetype_pokemon_map seed
    # doesn't match real observed team synergy -- real signal worth
    # surfacing, not a data-quality defect (its own dbt test already uses
    # severity=warn for the same reason, so its status can never actually
    # be "fail"; the exclusion here is belt-and-suspenders documentation
    # of that intent, not the only thing enforcing it).
    release_blocking_findings = [
        f"{entry.get('table_name') or entry.get('check_name') or entry.get('test_name') or entry.get('source_name')}: "
        f"status={entry['status']}"
        for entry in (
            *coverage_checks,
            *null_rate_checks,
            *duplicate_key_checks,
            *referential_integrity_checks,
            *row_count_anomaly_checks,
            *uncategorized_checks,
            *freshness_checks,
            *schema_drift_checks,
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
        "row_count_anomaly_checks": row_count_anomaly_checks,
        "uncategorized_checks": uncategorized_checks,
        "freshness_checks": freshness_checks,
        "schema_drift_checks": schema_drift_checks,
        "mart_quality_checks": mart_quality_checks,
        "archetype_drift_checks": archetype_drift_checks,
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

    The DuckDB warehouse is located as a sibling of `target_dir` (both live
    under `dbt/` -- `target_dir.parent / "data" / "warehouse.duckdb"`)
    rather than the module-level `DBT_WAREHOUSE_PATH` default, so a caller
    that points `target_dir` at a non-standard location (e.g. a test
    fixture) gets a consistently-located warehouse alongside it.
    """
    if dataset_version is None:
        dataset_version = latest_published_version()
    manifest = _load_json(target_dir / "manifest.json")
    run_results = _load_json(target_dir / "run_results.json")
    sources_path = target_dir / "sources.json"
    sources_result = json.loads(sources_path.read_text()) if sources_path.exists() else None
    warehouse_path = target_dir.parent / "data" / "warehouse.duckdb"
    report = build_report(manifest, run_results, dataset_version, sources_result, warehouse_path)
    write_report(report)
    return report
