# Implementation scaffold

## Purpose

This scaffold turns the documentation-only repository into a runnable project shell
for the Pokémon Champions dataset pipeline.

## Folder layout

- `configs/` — central pipeline settings and source metadata
- `data/raw/` — immutable source snapshots by adapter
- `data/staging/` — parsed source-specific intermediate outputs
- `data/normalized/` — joinable canonical and Champions entities
- `data/releases/` — versioned exports and changelog artifacts
- `data/manifests/` — execution metadata for refresh runs
- `schemas/v1/` — versioned contracts for entity definitions and manifests
- `src/champions_dataset/ingestion/` — source adapter scaffolding
- `src/champions_dataset/normalization/` — normalization phase scaffolding
- `src/champions_dataset/exports/` — release/publish phase scaffolding
- `src/champions_dataset/validation/` — validation entrypoints and checks
- `docs/` — implementation notes and data dictionary templates

## Phase mapping

- `ingest` → PRD milestone M2
- `normalize` → PRD milestone M3
- `publish` → PRD milestone M5
- `validate` → quality gates for definition-of-done checks

## Current behavior

The scaffold does not fetch live data yet. It produces a manifest describing:

- which source adapters are selected
- which output files each phase is expected to create
- which validation contracts exist before live extraction is implemented

## Next implementation steps

1. Replace planned source runs with live extraction logic per adapter.
2. Attach schema-aware parsers for canonical, Champions, and tournament entities.
3. Persist row counts, null-rate metrics, and duplicate-key checks in manifests.
4. Wire release generation to actual normalized datasets.
