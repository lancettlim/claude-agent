# claude-agent

This repository contains planning and specification documents for the Pokémon
Champions competitive data platform and its first dataset artifact.

## Current focus

The immediate goal is to define and deliver a reproducible v1 dataset package
covering canonical Pokémon data, Champions-specific adjustments, legality
snapshots, and tournament usage records.

## Repository documents

See `docs/` for the full document set:

- `docs/dataset-spec.md` — v1 dataset scope, schema, refresh policy, execution
  roadmap, and validation gates (source of truth for the v1 build)
- `docs/data-sources.md` — curated external sources and extraction notes
- `docs/prd.md` — product requirements for the competitive data platform
- `docs/business-case.md` — supporting business case document
- `docs/todo.md` — outstanding work items and definition of done for the v1
  release

`.claude/loop.md` documents how to use Claude Code's `/loop` skill against
this repo (implementation, backlog grooming, tech-debt cleanup, and
future-goal design loops).

## Repository structure

- `data/staging/` — raw source snapshots before normalization
- `data/normalized/` — normalized tables and derived outputs
- `data/marts/` — flat analytical exports/dashboard tables built from `data/normalized/`
- `dashboard/` — Streamlit analytics dashboard (M6) reading `data/marts/*.csv`; run via `make dashboard`
- `releases/manifests/` — versioned dataset manifests
- `releases/changelogs/` — versioned dataset changelogs
- `reports/validation/` — validation artifacts for release gates
