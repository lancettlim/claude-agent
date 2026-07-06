"""OP.GG Pokémon Champions extraction.

Contract: data/staging/opgg_champions.schema.json
Spec reference: docs/dataset-spec.md, "Source-specific extraction contracts > OP.GG Pokémon Champions"

Captures legal pool membership and rebalanced stat values from a JS-rendered
page (op.gg/pokemon-champions/pokedex), daily change detection. Not yet
implemented — this is Phase 1 (Ingestion) work; see docs/todo.md.

This extractor needs browser automation (the page has no API and is
JS-rendered). Playwright is already a project dependency (`make setup`
installs Chromium); the scraping logic itself — navigating and paginating
the legal pool, mapping fields to data/staging/opgg_champions.schema.json —
is still unimplemented.
"""

from __future__ import annotations

from pathlib import Path


def extract(output_path: Path) -> None:
    """Scrape the OP.GG legal pool + rebalanced stats and write them to
    output_path as CSV matching the field list in
    data/staging/opgg_champions.schema.json, including provenance fields."""
    raise NotImplementedError("OP.GG extraction is Phase 1 work, not yet implemented")
