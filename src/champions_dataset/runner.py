from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .exports import plan_publish
from .ingestion.registry import build_adapters
from .normalization import plan_normalization
from .shared.config import ensure_storage_layout, load_pipeline_config
from .shared.models import RunManifest, SourceRun
from .validation import run_validations


def run_pipeline(
    phase: str,
    selected_sources: Iterable[str] | None = None,
    output_root: Path | None = None,
    dry_run: bool = False,
) -> RunManifest:
    config = load_pipeline_config(output_root=output_root)
    if not dry_run:
        ensure_storage_layout(config.storage)

    source_names = list(selected_sources) if selected_sources else list(config.sources)
    phase_runs: list[SourceRun] = []

    if phase in {"ingest", "all"}:
        for adapter in build_adapters(config, source_names):
            phase_runs.append(adapter.plan_run(config.storage))

    if phase in {"normalize", "all"}:
        phase_runs.append(plan_normalization(config))

    if phase in {"publish", "all"}:
        phase_runs.append(plan_publish(config))

    validations = run_validations(config, source_names) if phase in {"validate", "all"} else []
    manifest = RunManifest(
        dataset_version=config.dataset_version,
        requested_phase=phase,
        selected_sources=source_names,
        dry_run=dry_run,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        phase_runs=phase_runs,
        validation_results=validations,
    )

    if not dry_run:
        write_manifest(config.storage.manifests_dir, manifest)

    return manifest


def write_manifest(manifests_dir: Path, manifest: RunManifest) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = manifests_dir / f"{timestamp}-{manifest.requested_phase}.json"
    path.write_text(json.dumps(manifest.to_dict(), indent=2) + "\n", encoding="utf-8")
    return path
