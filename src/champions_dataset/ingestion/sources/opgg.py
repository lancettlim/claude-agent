from __future__ import annotations

from champions_dataset.ingestion.base import SourceAdapter
from champions_dataset.shared.models import SourceDefinition


def build_opgg_adapter(definition: SourceDefinition) -> SourceAdapter:
    return SourceAdapter(
        definition=definition,
        entity_targets=["pokemon_stat_champions", "legality_snapshot"],
        extraction_notes=[
            "Snapshot legal-pool and custom stat pages before parsing derived tables.",
            "Reserve a join path back to canonical PokéAPI identifiers.",
        ],
    )
