# TODO

Outstanding work for the v1 Pokémon Champions dataset artifact, derived from
`V1-DATASET-SPEC.md` and `PRD.md`.

## Repository scaffolding

- [x] Create placeholder directories for staging, normalized, manifests,
  changelogs, and validation reports (`data/`, `releases/`, `reports/`)
- [x] Add a `manifest.json` starter template (`releases/manifests/manifest.template.json`)
- [ ] Add a `CHANGELOG.md` starter template (`releases/changelogs/`)
- [ ] Add example/schema files for staging snapshots (`data/staging/`)
- [ ] Add example/schema files for normalized tables (`data/normalized/`)
- [ ] Add a validation report template (`reports/validation/`)

## Phase 1 — Ingestion

- [ ] Implement extraction contract for PokéAPI (pokemon identity + base stats)
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

- [ ] PokéBase app ingestion (regulation-specific restrictions)
- [ ] Limitless VGC ingestion (historical event coverage)
- [ ] Victory Road ingestion (moveset/EV enrichment)
