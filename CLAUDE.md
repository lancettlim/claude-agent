# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository purpose

This repository holds planning, specification, and directory scaffolding for
the **Pokémon Champions Competitive Data Platform** — a project to build a
unified, versioned dataset combining canonical Pokémon game data,
Champions-format balance changes, legality snapshots, and tournament usage
data. The repository is currently documentation and scaffolding: the v1 build
has a working scaffold (`pipelines/` + `dbt/`, see "Development workflow"
below) but no real extraction/normalization logic has been implemented yet —
that is Phase 1+ work tracked in `docs/todo.md`.

## Document map

Read these in order to understand the project; each narrows scope from the
previous:

- `README.md` — repository overview and current focus; links to the other docs
- `docs/business-case.md` — why this exists: problem statement, value
  drivers, risks, recommendation
- `docs/prd.md` — product requirements: goals, scope/non-goals, functional and
  non-functional requirements, milestones (M1–M6)
- `docs/dataset-spec.md` — the authoritative spec for the v1 dataset: entity
  dictionary, primary/join keys, refresh policy, release package contents,
  validation gates, and the phased execution roadmap. This is the most
  detailed and most likely to be updated as work progresses.
- `docs/data-sources.md` — catalog of external data sources with extraction
  notes, including which are in v1 scope vs. deferred to later phases
- `docs/todo.md` — outstanding work items and the v1 definition-of-done
  checklist

`.claude/loop.md` is Claude-Code-specific operating guidance (not part of
the docs/ narrative above): it defines four `/loop` modes for this repo —
implementation, backlog grooming, tech debt, and future-goal design.

When these documents disagree on scope or details, `docs/dataset-spec.md` is
the most current source of truth for the v1 build; `docs/prd.md` is the
source of truth for product-level goals/non-goals.

## V1 scope at a glance

- **In-scope sources (v1)**: PokéAPI (canonical stats), OP.GG Pokémon
  Champions (legal pool + rebalanced stats), MunchStats (tournament/roster
  usage)
- **Deferred sources**: PokéBase app, Limitless VGC, Victory Road (see
  `docs/dataset-spec.md` for why)
- **Core entities**: `pokemon`, `pokemon_stat_canonical`,
  `pokemon_stat_champions`, `pokemon_stat_delta`, `legality_snapshot`,
  `tournament_event`, `tournament_team`, `tournament_team_member`
- **Release package**: one CSV per core entity plus `manifest.json` and
  `CHANGELOG.md`, versioned as `MAJOR.MINOR.PATCH`

## Repository structure

```
data/
  staging/                # raw source snapshots before normalization (not release outputs)
  normalized/              # normalized, join-ready tables built from staging
releases/
  manifests/               # one manifest.json per published dataset version
  changelogs/               # one changelog entry per dataset version
reports/
  validation/               # coverage, null-rate, duplicate-key, referential-integrity reports
```

Each of these directories currently contains only a placeholder `README.md`
describing its intended contents — no data has been ingested yet. When
implementing ingestion/normalization work, respect this layout:
staging → normalized → releases, with validation reports gating what may be
published to `releases/`.

## Conventions to follow when extending this repo

- **Provenance is mandatory.** Per `docs/dataset-spec.md`, every record in
  every table must carry `source_name`, `source_url`, `source_record_id`,
  `extracted_at_utc`, and `dataset_version`. Records without traceable source
  identity must not ship in release outputs.
- **Respect the entity/key contracts.** Use the primary keys and join keys
  defined in `docs/dataset-spec.md` (e.g. `pokemon_key` as the cross-source
  identity, `pokemon_id` as the canonical Pokédex ID) rather than inventing
  new ones.
- **Don't ship ungated data.** Anything landing in `releases/` should have
  passed the coverage, null-rate, duplicate-key, and referential-integrity
  gates described in `docs/dataset-spec.md`, with results recorded under
  `reports/validation/`.
- **Keep staging separate from release outputs.** Raw/staged snapshots in
  `data/staging/` are inputs, not deliverables — normalization and
  validation happen before anything is promoted toward `releases/`.
- **Update docs alongside scope changes.** If v1 scope, schema, or refresh
  policy changes, update `docs/dataset-spec.md` (and `docs/prd.md` if
  goals/scope change) rather than letting the docs drift from actual
  implementation.

## Development workflow

Python, managed with `uv`. Setup and the standard dev loop:

```
make setup      # uv sync + playwright install --with-deps chromium
make check      # lint + unit tests + dbt build/test + validation report
```

Individual targets: `make lint` (ruff), `make test` (pytest), `make dbt-build`
(`cd dbt && dbt build`), `make validate` (runs dbt build, then writes
`reports/validation/validation_report.json`).

- `pipelines/extract/` — one module per v1 source (PokéAPI, OP.GG, MunchStats)
  that writes provenance-tagged rows into `data/staging/`. Currently stubs
  (`NotImplementedError`) — implementing these is Phase 1 work.
- `dbt/` — a dbt-duckdb project that reads `data/staging/*.csv` as sources,
  normalizes into `data/normalized/*.csv` (external-materialized models,
  currently typed empty stubs pending Phase 2), and encodes the
  `docs/dataset-spec.md` release gates (coverage, null-rate, duplicate-key,
  referential-integrity) as singular tests under `dbt/tests/singular/`.
- `pipelines/validate/report.py` — reshapes dbt's test results into
  `reports/validation/validation_report.json`, matching
  `reports/validation/validation_report.template.json`'s shape exactly.
- `tests/` — pytest unit tests, mirroring the `pipelines/` package.

Playwright is a project dependency (`make setup` installs Chromium) for the
OP.GG extractor's JS-rendered page — the scraping logic itself is still
unimplemented (Phase 1 work).
