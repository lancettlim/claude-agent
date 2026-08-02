"""Generate reports/validation/extraction_summary.json from real extraction
runs (backlog.md #48).

This file used to be a hand-written snapshot -- "what someone observed the
last time they ran the extractors" -- with no code generating or updating
it, so it silently went stale (it was still dated 2026-07-19 while the
pipeline moved on). This module makes it real: `pipelines.cli`'s
`_run_extract` calls `update()` once per staging subdirectory actually
written during an extraction run (PokéAPI's move/ability/item detail
fetches each get their own entry, not just one merged "PokéAPI" entry --
the old hand-written file didn't account for those requests at all).
`update()` merges just that source's entry into the existing document
(every other source's most-recently-recorded entry is preserved
untouched), so a single-source `extract <source>` run doesn't wipe out
what's known about the other sources.

Distinct from pipelines/validate/report.py's validation_report.json: this
is a Phase 1 ingestion check (did we reach the source, how many rows came
back, how many required fields were null) rather than a normalized-table
release gate.

Request counts come from pipelines.extract.http.RequestStats, populated by
wrapping an extraction call in `http.track_requests()` -- every extractor's
raw HTTP calls already funnel through `http.get_with_retry`, so that's the
one chokepoint instrumented, rather than touching each extractor module.
required_field_null_rate is computed directly from the written CSV against
the same data/staging/<subdir>.schema.json contract's `required: true`
fields dataset-spec.md already treats as authoritative -- not a
hand-maintained number.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipelines.extract.http import RequestStats

REPO_ROOT = Path(__file__).resolve().parents[2]
STAGING_SCHEMA_DIR = REPO_ROOT / "data" / "staging"
SUMMARY_PATH = REPO_ROOT / "reports" / "validation" / "extraction_summary.json"

DESCRIPTION = (
    "Phase 1 ingestion check: source availability and row-level parsing success "
    "for each staging extractor. Distinct from validation_report.json, which "
    "gates normalized-table release readiness."
)


@dataclass
class SourceRunResult:
    """Everything one `_run_tracked_extract` call in pipelines.cli knows
    about a single staging subdirectory's extraction after it finishes (or
    fails)."""

    source_name: str
    endpoint: str
    staging_subdir: str
    output_path: Path
    stats: RequestStats
    error: str | None = None


def _schema_path(staging_subdir: str) -> Path:
    return STAGING_SCHEMA_DIR / f"{staging_subdir}.schema.json"


def required_fields(staging_subdir: str) -> list[str]:
    """Field names data/staging/<staging_subdir>.schema.json marks
    `required: true`. Missing schema file (shouldn't happen for a real
    source, but a test double might not provide one) -> no fields, so the
    null-rate calculation below degrades to 0.0 rather than raising."""
    schema_path = _schema_path(staging_subdir)
    if not schema_path.exists():
        return []
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return [f["name"] for f in schema.get("fields", []) if f.get("required")]


def rows_and_required_field_null_rate(output_path: Path, fields: list[str]) -> tuple[int, float]:
    """(row count, fraction of required-field cells that are null/blank)
    for the CSV at output_path. Only fields marked `required: true` count
    toward the denominator -- a field the schema itself says is optional
    (e.g. OP.GG's pokemon_id, blank for Mega/regional forms) isn't a
    quality problem, so it shouldn't move this number."""
    if not output_path.exists() or not fields:
        return 0, 0.0
    with output_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        return 0, 0.0
    total_cells = len(rows) * len(fields)
    null_cells = sum(1 for row in rows for name in fields if not row.get(name))
    return len(rows), round(null_cells / total_cells, 4)


def _availability(result: SourceRunResult) -> str:
    if result.error is not None:
        return f"unreachable: {result.error}"
    stats = result.stats
    if stats.attempted == 0:
        return "no requests attempted"
    if stats.succeeded == stats.attempted:
        return "reachable, HTTP 200 for all requests"
    failed = stats.attempted - stats.succeeded
    return f"reachable, but {failed}/{stats.attempted} request(s) failed"


def build_source_entry(result: SourceRunResult) -> dict[str, Any]:
    """One `sources[]` entry, matching the shape the prior hand-written
    extraction_summary.json used (endpoint/availability/requests_attempted/
    requests_succeeded/request_success_rate/rows_written/
    required_field_null_rate), computed from real run data instead of
    observed-and-typed-up-by-hand. `checked_at_utc` is this entry's own
    timestamp -- distinct from the document-level `generated_at_utc`,
    which reflects whichever source's `update()` call ran most recently
    and is misleading for every *other* entry `update()` left untouched
    (see `merge_source_entry`)."""
    rows_written, null_rate = rows_and_required_field_null_rate(
        result.output_path, required_fields(result.staging_subdir)
    )
    stats = result.stats
    return {
        "source_name": result.source_name,
        "endpoint": result.endpoint,
        "availability": _availability(result),
        "requests_attempted": stats.attempted,
        "requests_succeeded": stats.succeeded,
        "request_success_rate": (
            round(stats.success_rate, 4) if stats.success_rate is not None else None
        ),
        "rows_written": rows_written,
        "required_field_null_rate": null_rate,
        "checked_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def merge_source_entry(document: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any]:
    """Replace `document`'s entry for entry["source_name"] (if any) with
    `entry`, leaving every other source's most-recently-recorded entry
    untouched -- so a single-source `extract <source>` run only updates
    the one entry it actually ran, not the whole document."""
    sources = [
        s for s in document.get("sources", []) if s.get("source_name") != entry["source_name"]
    ]
    sources.append(entry)
    sources.sort(key=lambda s: s["source_name"])
    return {**document, "sources": sources}


def load_document(path: Path = SUMMARY_PATH) -> dict[str, Any]:
    if not path.exists():
        return {
            "description": DESCRIPTION,
            "generated_at_utc": None,
            "dataset_version": None,
            "sources": [],
        }
    return json.loads(path.read_text(encoding="utf-8"))


def write_document(document: dict[str, Any], path: Path = SUMMARY_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def update(
    result: SourceRunResult,
    *,
    dataset_version: str,
    path: Path = SUMMARY_PATH,
) -> dict[str, Any]:
    """Merge `result`'s entry into the extraction summary document at
    `path` and write it back. Returns the full updated document."""
    document = load_document(path)
    entry = build_source_entry(result)
    document = merge_source_entry(document, entry)
    document["description"] = DESCRIPTION
    document["dataset_version"] = dataset_version
    document["generated_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    write_document(document, path)
    return document
