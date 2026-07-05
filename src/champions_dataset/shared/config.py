from __future__ import annotations

import json
from pathlib import Path

from .models import PipelineConfig, SourceDefinition, StorageLayout

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = REPO_ROOT / "configs" / "pipeline.json"


def load_pipeline_config(output_root: Path | None = None) -> PipelineConfig:
    raw_config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    resolved_output_root = (output_root or REPO_ROOT / "data").resolve()
    storage = StorageLayout(
        output_root=resolved_output_root,
        raw_dir=resolved_output_root / "raw",
        staging_dir=resolved_output_root / "staging",
        normalized_dir=resolved_output_root / "normalized",
        releases_dir=resolved_output_root / "releases",
        manifests_dir=resolved_output_root / "manifests",
        schema_dir=REPO_ROOT / "schemas",
        docs_dir=REPO_ROOT / "docs",
    )
    sources = {
        name: SourceDefinition(name=name, **definition)
        for name, definition in raw_config["sources"].items()
    }
    return PipelineConfig(
        dataset_version=raw_config["dataset_version"],
        default_phase=raw_config["default_phase"],
        sources=sources,
        storage=storage,
    )


def ensure_storage_layout(storage: StorageLayout) -> None:
    for directory in (
        storage.raw_dir,
        storage.staging_dir,
        storage.normalized_dir,
        storage.releases_dir,
        storage.manifests_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)
