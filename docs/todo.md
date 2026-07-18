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
- [x] Add `dbt/` project: staging sources, normalized models (see Phase 2),
  and singular tests encoding the coverage/null-rate/duplicate-key/
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
- [x] Implement extraction contract for OP.GG Pokémon Champions (legal pool +
  rebalanced stats)
- [x] Implement extraction contract for MunchStats (tournament/team/roster data)
- [x] Land staging outputs with raw snapshots and extraction metadata
- [x] Validate source availability and row-level parsing success thresholds
  (see `reports/validation/extraction_summary.json`: 100% request success
  and 0% required-field null rate across all three sources)

## Phase 2 — Normalization

- [x] Standardize IDs and join keys (`pokemon_key`, `pokemon_id`) across
  canonical, Champions, and tournament data (`dbt/models/normalized/pokemon.sql`
  + `dbt/models/intermediate/`; PokéAPI extraction now covers Mega/regional/
  alternate forms too, and `dbt/seeds/*.csv` hold the controlled OP.GG- and
  MunchStats-name-to-PokéAPI-form mappings dataset-spec.md calls for)
- [x] Build `pokemon_stat_delta` (canonical vs Champions) outputs
- [x] Generate regulation-aware `legality_snapshot` outputs (`regulation_code`
  is currently always null — OP.GG's Champions Pokédex page doesn't publish
  regulation codes, a pre-existing known risk in
  `data/staging/opgg_champions.schema.json` — so this table's null-rate gate
  fails until a regulation-code source is added; tracked below)
- [x] Normalize `tournament_event`, `tournament_team`, `tournament_team_member`
  (`dbt/models/intermediate/int_munchstats_deduped.sql` also resolves 9
  upstream MunchStats teams that were double-recorded under two placements)

## Phase 3 — Analytics and dashboard outputs

- [ ] Publish flat analytical exports and summary aggregates
- [ ] Provide dashboard-ready trend tables (usage, legality, stat changes)
- [ ] Document KPI views and filter dimensions (regulation/date/tournament tier)

## Release readiness (v1 definition of done)

- [x] Coverage: >=95% of OP.GG legal pool mapped to canonical `pokemon_id`
  (currently 98.4%, 312/317 legal-pool rows; see
  `reports/validation/validation_report.json`)
- [x] Coverage: >=90% of targeted tournament records mapped to normalized team
  tables (currently ~99.9%)
- [ ] Data quality: required-field null rate <=1% for core tables
  (`legality_snapshot` fails at ~9.1% — `regulation_code` is always null,
  pending a regulation-code source; every other core table passes)
- [x] Data quality: zero duplicate primary-key violations
- [x] Data quality: referential integrity checks pass for Pokémon/team/event
  joins
- [x] Export: versioned CSV outputs for all core entities (`pipelines/release/build.py`,
  `python -m pipelines.cli release --version X.Y.Z`; correctly refuses to
  publish right now because of the `legality_snapshot` null-rate gap above —
  confirmed by running it)
- [x] Export: versioned JSON manifest with source lineage and run stats (same
  command; also writes `releases/changelogs/CHANGELOG-<version>.md`)
- [x] Validate example analysis queries (`dbt/analyses/`, see its `README.md`):
  top stat gainers/losers and most-used legal Pokémon both validated with
  real, non-degenerate results; largest legal-pool changes by regulation is
  structurally validated but currently degenerate (single null
  `regulation_code`, single `snapshot_date` — same regulation-code gap plus
  no second extraction run yet to diff against)

## Deferred (post-v1)

See "Deferred sources" in `dataset-spec.md` for the list of sources
(PokéBase app, Limitless VGC, Victory Road) and the rationale for deferring
each one past v1.
