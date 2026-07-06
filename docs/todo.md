# TODO

Outstanding work for the v1 Pokémon Champions dataset artifact, derived from
`dataset-spec.md` and `prd.md`.

## Repository scaffolding

- [x] Create placeholder directories for staging, normalized, manifests,
  changelogs, and validation reports (`data/`, `releases/`, `reports/`)
- [x] Add a `manifest.json` starter template (`releases/manifests/manifest.template.json`)
- [x] Add a `CHANGELOG.md` starter template (`releases/changelogs/CHANGELOG.template.md`)
- [x] Add example/schema files for staging snapshots (`data/staging/*.schema.json`)
- [x] Add example/schema files for normalized tables (`data/normalized/*.schema.json`)
- [x] Add a validation report template (`reports/validation/validation_report.template.json`)

## Tooling

- [x] Add `pyproject.toml`/`uv.lock`-managed Python environment (pandas,
  requests, dbt-core, dbt-duckdb, pytest, ruff)
- [x] Add `pipelines/` package skeleton (`extract/` stubs per source,
  `validate/report.py`, `cli.py`)
- [x] Add `dbt/` project: staging sources, typed-empty normalized stub
  models, and singular tests encoding the coverage/null-rate/duplicate-key/
  referential-integrity gates from `dataset-spec.md`
- [x] Add `Makefile` with `setup`/`lint`/`test`/`dbt-build`/`validate`/`check`
  targets
- [x] Update `CLAUDE.md` and `.claude/loop.md` to reflect the build/test
  system
- [x] Add the Playwright dependency and browser-install step (`make setup`
  installs Chromium); implementing the OP.GG scraper itself is tracked
  under "Phase 1 — Ingestion" below

## Phase 1 — Ingestion

- [x] Implement extraction contract for PokéAPI (pokemon identity + base stats)
- [ ] Implement extraction contract for OP.GG Pokémon Champions (legal pool +
  rebalanced stats)
- [ ] Implement extraction contract for MunchStats (tournament/team/roster data)
- [ ] Land staging outputs with raw snapshots and extraction metadata
- [ ] Validate source availability and row-level parsing success thresholds

## Phase 2 — Normalization

- [ ] Standardize IDs and join keys (`pokemon_key`, `pokemon_id`) across
  canonical, Champions, and tournament data
- [ ] Build `pokemon_stat_delta` (canonical vs Champions) outputs
- [ ] Generate regulation-aware `legality_snapshot` outputs
- [ ] Normalize `tournament_event`, `tournament_team`, `tournament_team_member`

## Phase 3 — Analytics and dashboard outputs

- [ ] Publish flat analytical exports and summary aggregates
- [ ] Provide dashboard-ready trend tables (usage, legality, stat changes)
- [ ] Document KPI views and filter dimensions (regulation/date/tournament tier)

## Release readiness (v1 definition of done)

- [ ] Coverage: >=95% of OP.GG legal pool mapped to canonical `pokemon_id`
- [ ] Coverage: >=90% of targeted tournament records mapped to normalized team
  tables
- [ ] Data quality: required-field null rate <=1% for core tables
- [ ] Data quality: zero duplicate primary-key violations
- [ ] Data quality: referential integrity checks pass for Pokémon/team/event
  joins
- [ ] Export: versioned CSV outputs for all core entities
- [ ] Export: versioned JSON manifest with source lineage and run stats
- [ ] Validate example analysis queries (top stat gainers/losers, most-used
  legal Pokémon, largest legal-pool changes by regulation)

## Deferred (post-v1)

See "Deferred sources" in `dataset-spec.md` for the list of sources
(PokéBase app, Limitless VGC, Victory Road) and the rationale for deferring
each one past v1.
