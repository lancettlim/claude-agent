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
