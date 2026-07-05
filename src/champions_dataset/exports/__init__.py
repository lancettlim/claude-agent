from __future__ import annotations

from champions_dataset.shared.models import PipelineConfig, SourceRun


RELEASE_OUTPUTS = [
    "releases/v1/core-entities.csv",
    "releases/v1/core-entities.json",
    "releases/v1/manifest.json",
    "releases/v1/changelog.md",
]


def plan_publish(config: PipelineConfig) -> SourceRun:
    return SourceRun(
        component="publish",
        phase="publish",
        status="planned",
        outputs=[str(config.storage.output_root / path) for path in RELEASE_OUTPUTS],
        notes=[
            "Package versioned flat files for downstream analysis consumers.",
            "Emit release metadata with lineage, row counts, and execution timestamps.",
            "Reserve changelog output for schema changes and major refresh deltas.",
        ],
    )
