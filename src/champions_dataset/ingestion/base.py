from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from champions_dataset.shared.models import SourceDefinition, SourceRun, StorageLayout


@dataclass
class SourceAdapter:
    definition: SourceDefinition
    entity_targets: list[str]
    extraction_notes: list[str]

    def plan_run(self, storage: StorageLayout) -> SourceRun:
        outputs = [
            str(storage.output_root / target)
            for target in (
                self.definition.raw_targets
                + self.definition.staging_targets
                + self.definition.normalized_targets
            )
        ]
        notes = [
            self.definition.description,
            f"Entities: {', '.join(self.entity_targets)}",
            *self.extraction_notes,
        ]
        return SourceRun(
            component=self.definition.name,
            phase="ingest",
            status="planned",
            outputs=outputs,
            notes=notes,
            source_url=self.definition.url,
            cadence=self.definition.cadence,
        )
