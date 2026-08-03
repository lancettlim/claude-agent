"""Load and assert against the data/staging/*.schema.json and
data/normalized/*.schema.json contracts (backlog.md #41).

Both directories' schema.json files are documented in CLAUDE.md as "the
durable, tracked contract" for their respective layer, but until this
module existed nothing actually loaded or compared against them: every
`stg_*.sql` model is a bare `select *`, so a column added, renamed, or
dropped -- whether from an upstream source's shape changing or simply a
staging FIELDNAMES/schema.json edit drifting out of sync with each other
-- would propagate silently through the normalized layer and only surface
much later as a confusing "column not found" error in some unrelated
downstream model, with no indication of where the real mismatch was
introduced.

This module is deliberately just field-name-list comparison, not full
JSON Schema validation (types, nullability) -- the fields these contracts
document (`required`/`type`/`description`) are richer than that, but a
name-list mismatch is the actual failure mode described above (a rename
or reorder), and it's cheap enough to run on every test suite invocation
with no real data needed for the staging half.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


def schema_field_names(schema_path: Path) -> list[str]:
    """The `fields[].name` list from a data/staging/*.schema.json or
    data/normalized/*.schema.json contract file, in declared order."""
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return [field["name"] for field in schema["fields"]]


def csv_header(csv_path: Path) -> list[str]:
    with csv_path.open(newline="", encoding="utf-8") as fh:
        return next(csv.reader(fh), [])


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STAGING_DIR = REPO_ROOT / "data" / "staging"


def staging_contract_mismatches(staging_dir: Path = DEFAULT_STAGING_DIR) -> list[str]:
    """Reasons the staging snapshots on disk can't be built against, one
    string per problem; empty means every declared source is present and
    matches its contract.

    This exists for CI (backlog.md #35), which never extracts anything
    itself -- it restores the actions/cache entry the scheduled extraction
    workflow populates and runs dbt against that. The cache is therefore
    always as old as the last scheduled run, so any PR that adds a source
    or a staging column is guaranteed to be building against snapshots that
    predate it: a new source has no directory at all, and an existing
    source's CSVs are missing the new column. Both surface as opaque dbt
    errors ("No files found that match the pattern ...",
    "Referenced column ... not found in FROM clause") that look like code
    defects but aren't -- they resolve on their own once the next scheduled
    extraction repopulates the cache.

    The workflow already meant to skip rather than fail in this situation;
    it just only recognised the total-miss case (a fresh fork with no cache
    at all). This makes the partial-staleness case recognisable too.
    """
    mismatches: list[str] = []
    for schema_path in sorted(staging_dir.glob("*.schema.json")):
        source = schema_path.name.removesuffix(".schema.json")
        snapshots = sorted((staging_dir / source).glob("*.csv"))
        if not snapshots:
            mismatches.append(
                f"{source}: no staged snapshot (source added since the cache was built)"
            )
            continue
        expected = schema_field_names(schema_path)
        # Only the newest snapshot needs to match: dbt's staging models
        # union every retained snapshot, so an older one with a narrower
        # header is exactly the drift being reported here.
        header = csv_header(snapshots[-1])
        if header != expected:
            missing = [name for name in expected if name not in header]
            extra = [name for name in header if name not in expected]
            detail = ", ".join(
                part
                for part in (
                    f"missing {missing}" if missing else "",
                    f"unexpected {extra}" if extra else "",
                    "column order differs" if not missing and not extra else "",
                )
                if part
            )
            mismatches.append(
                f"{source}: {snapshots[-1].name} does not match its contract ({detail})"
            )
    return mismatches


if __name__ == "__main__":  # pragma: no cover -- CI entry point, see above
    import sys

    problems = staging_contract_mismatches()
    for problem in problems:
        print(problem)
    sys.exit(1 if problems else 0)
