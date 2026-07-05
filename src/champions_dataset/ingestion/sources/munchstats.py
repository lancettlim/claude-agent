from __future__ import annotations

from champions_dataset.ingestion.base import SourceAdapter
from champions_dataset.shared.models import SourceDefinition


def build_munchstats_adapter(definition: SourceDefinition) -> SourceAdapter:
    return SourceAdapter(
        definition=definition,
        entity_targets=["tournament_event", "tournament_team", "tournament_team_member"],
        extraction_notes=[
            "Flatten nested roster payloads into event, team, and team-member staging sets.",
            "Preserve tournament provenance for downstream usage analytics.",
        ],
    )
