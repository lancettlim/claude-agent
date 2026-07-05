from __future__ import annotations

from pathlib import Path

from champions_dataset.shared.models import PipelineConfig, ValidationResult


REQUIRED_SCHEMA_FILES = [
    "v1/core-entities.schema.json",
    "v1/run-manifest.schema.json",
]


def run_validations(config: PipelineConfig, selected_sources: list[str]) -> list[ValidationResult]:
    results = [
        _validate_selected_sources(config, selected_sources),
        _validate_storage_layout(config),
        _validate_schema_files(config.storage.schema_dir),
        _validate_lineage_requirements(config),
    ]
    return results


def _validate_selected_sources(config: PipelineConfig, selected_sources: list[str]) -> ValidationResult:
    missing = [name for name in selected_sources if name not in config.sources]
    if missing:
        return ValidationResult(
            name="source-selection",
            status="fail",
            message=f"Unsupported sources requested: {', '.join(missing)}",
        )
    return ValidationResult(
        name="source-selection",
        status="pass",
        message="All requested source adapters are defined in the central pipeline config.",
    )


def _validate_storage_layout(config: PipelineConfig) -> ValidationResult:
    expected = [
        config.storage.raw_dir,
        config.storage.staging_dir,
        config.storage.normalized_dir,
        config.storage.releases_dir,
        config.storage.manifests_dir,
    ]
    missing = [str(path) for path in expected if not path.exists()]
    if missing:
        return ValidationResult(
            name="storage-layout",
            status="warn",
            message=f"Storage directories missing for current output root: {', '.join(missing)}",
        )
    return ValidationResult(
        name="storage-layout",
        status="pass",
        message="Raw, staging, normalized, release, and manifest directories are present.",
    )


def _validate_schema_files(schema_dir: Path) -> ValidationResult:
    missing = []
    for relative_path in REQUIRED_SCHEMA_FILES:
        schema_path = schema_dir / relative_path
        if not schema_path.exists():
            missing.append(str(schema_path))
    if missing:
        return ValidationResult(
            name="schema-contracts",
            status="fail",
            message=f"Missing schema artifacts: {', '.join(missing)}",
        )
    return ValidationResult(
        name="schema-contracts",
        status="pass",
        message="Core entity and run-manifest schema artifacts are committed.",
    )


def _validate_lineage_requirements(config: PipelineConfig) -> ValidationResult:
    incomplete = [name for name, source in config.sources.items() if not source.url or not source.cadence]
    if incomplete:
        return ValidationResult(
            name="lineage-rules",
            status="fail",
            message=f"Lineage metadata incomplete for: {', '.join(incomplete)}",
        )
    return ValidationResult(
        name="lineage-rules",
        status="pass",
        message="Each source definition includes source URL and refresh cadence metadata.",
    )
