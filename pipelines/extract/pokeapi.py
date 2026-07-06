"""PokéAPI extraction.

Contract: data/staging/pokeapi.schema.json
Spec reference: docs/dataset-spec.md, "Source-specific extraction contracts > PokéAPI"

Captures Pokémon/form identity rows and base stat rows for all Pokémon in the
mapped Champions pool, weekly refresh cadence. Not yet implemented — this is
Phase 1 (Ingestion) work; see docs/todo.md.
"""

from __future__ import annotations

from pathlib import Path


def extract(output_path: Path) -> None:
    """Fetch PokéAPI identity + base stat rows and write them to output_path
    as CSV matching the field list in data/staging/pokeapi.schema.json,
    including provenance fields (source_name, source_url, source_record_id,
    extracted_at_utc, dataset_version)."""
    raise NotImplementedError("PokéAPI extraction is Phase 1 work, not yet implemented")
