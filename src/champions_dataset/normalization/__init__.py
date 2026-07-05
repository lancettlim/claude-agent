from __future__ import annotations

from champions_dataset.shared.models import PipelineConfig, SourceRun


NORMALIZED_OUTPUTS = [
    "normalized/pokemon_stat_delta.parquet",
    "normalized/legality_snapshot.parquet",
    "normalized/tournament_team_member.parquet",
    "normalized/pokemon_identity_map.parquet",
]


def plan_normalization(config: PipelineConfig) -> SourceRun:
    return SourceRun(
        component="normalization",
        phase="normalize",
        status="planned",
        outputs=[str(config.storage.output_root / path) for path in NORMALIZED_OUTPUTS],
        notes=[
            "Standardize pokemon_id and form_name join keys across all sources.",
            "Produce canonical-vs-Champions stat deltas and regulation-aware legality snapshots.",
            "Persist tournament entities in release-ready normalized tables.",
        ],
    )
