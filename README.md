# claude-agent

This repository contains planning and specification documents for the Pokémon
Champions competitive data platform and its first dataset artifact.

## Current focus

The immediate goal is to define and deliver a reproducible v1 dataset package
covering canonical Pokémon data, Champions-specific adjustments, legality
snapshots, and tournament usage records.

## Repository documents

- `V1-DATASET-SPEC.md` — v1 dataset scope, schema, refresh policy, execution
  roadmap, and definition of done
- `DATASET.md` — curated external sources and extraction notes
- `PRD.md` — product requirements for the competitive data platform
- `champions-business-case.md` — supporting business case document
- `TODO.md` — outstanding work items toward the v1 release

## Repository structure

- `data/staging/` — raw source snapshots before normalization
- `data/normalized/` — normalized tables and derived outputs
- `releases/manifests/` — versioned dataset manifests
- `releases/changelogs/` — versioned dataset changelogs
- `reports/validation/` — validation artifacts for release gates
