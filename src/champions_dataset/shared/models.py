from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class StorageLayout:
    output_root: Path
    raw_dir: Path
    staging_dir: Path
    normalized_dir: Path
    releases_dir: Path
    manifests_dir: Path
    schema_dir: Path
    docs_dir: Path


@dataclass(frozen=True)
class SourceDefinition:
    name: str
    url: str
    cadence: str
    description: str
    raw_targets: list[str]
    staging_targets: list[str]
    normalized_targets: list[str]


@dataclass(frozen=True)
class PipelineConfig:
    dataset_version: str
    default_phase: str
    sources: dict[str, SourceDefinition]
    storage: StorageLayout


@dataclass(frozen=True)
class SourceRun:
    component: str
    phase: str
    status: str
    outputs: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    source_url: str | None = None
    cadence: str | None = None
    record_count: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "phase": self.phase,
            "status": self.status,
            "outputs": self.outputs,
            "notes": self.notes,
            "source_url": self.source_url,
            "cadence": self.cadence,
            "record_count": self.record_count,
        }


@dataclass(frozen=True)
class ValidationResult:
    name: str
    status: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
        }


@dataclass(frozen=True)
class RunManifest:
    dataset_version: str
    requested_phase: str
    selected_sources: list[str]
    dry_run: bool
    generated_at_utc: str
    phase_runs: list[SourceRun] = field(default_factory=list)
    validation_results: list[ValidationResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_version": self.dataset_version,
            "requested_phase": self.requested_phase,
            "selected_sources": self.selected_sources,
            "dry_run": self.dry_run,
            "generated_at_utc": self.generated_at_utc,
            "phase_runs": [run.to_dict() for run in self.phase_runs],
            "validation_results": [result.to_dict() for result in self.validation_results],
        }
