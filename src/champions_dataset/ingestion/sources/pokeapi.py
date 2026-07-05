from __future__ import annotations

from champions_dataset.ingestion.base import SourceAdapter
from champions_dataset.shared.models import SourceDefinition


def build_pokeapi_adapter(definition: SourceDefinition) -> SourceAdapter:
    return SourceAdapter(
        definition=definition,
        entity_targets=["pokemon", "pokemon_stat_canonical"],
        extraction_notes=[
            "Capture canonical Pokémon, move, and item reference tables.",
            "Preserve raw CSV lineage before any normalization steps.",
        ],
    )
