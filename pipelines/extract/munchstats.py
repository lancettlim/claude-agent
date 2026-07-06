"""MunchStats extraction.

Contract: data/staging/munchstats.schema.json
Spec reference: docs/dataset-spec.md, "Source-specific extraction contracts > MunchStats"

Captures tournament metadata, team metadata, and team-member Pokémon rows
from structured JSON, daily check with publish after new event detection.
Not yet implemented — this is Phase 1 (Ingestion) work; see docs/todo.md.
"""

from __future__ import annotations

from pathlib import Path


def extract(output_path: Path) -> None:
    """Fetch MunchStats tournament/team/roster JSON, flatten nested team
    arrays into one row per team member, and write to output_path as CSV
    matching the field list in data/staging/munchstats.schema.json,
    including provenance fields."""
    raise NotImplementedError("MunchStats extraction is Phase 1 work, not yet implemented")
