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
- [x] Implement extraction contract for PokéBase (per-regulation legal-pool
  membership; pulled into v1 scope — see "V1 scope" in `dataset-spec.md` —
  once OP.GG proved insufficient for `legality_snapshot.regulation_code`)
- [x] Land staging outputs with raw snapshots and extraction metadata
- [x] Validate source availability and row-level parsing success thresholds
  (see `reports/validation/extraction_summary.json`: 100% request success
  and 0% required-field null rate across all four sources)
- [x] Extend MunchStats extraction (`pipelines/extract/munchstats.py`) to
  additionally capture `metadata.json`'s `type` field (tournament tier,
  e.g. "International"), `players.json`'s `record` field (win-rate proxy),
  and team-member `item`/`ability`/`tera_type`/`moves` fields — only
  `pokemon` is captured per slot today; update
  `data/staging/munchstats.schema.json` to match (see the gap noted in
  `dbt/models/marts/schema.yml`)
  (staging CSV now carries `event_tier`, `record_wins`/`record_losses`,
  `item_name`, `ability`, `tera_type`, and pipe-delimited `moves`; still
  raw/unmapped — Phase 2 normalizes these into the entity dictionary)

## Phase 2 — Normalization

- [x] Standardize IDs and join keys (`pokemon_key`, `pokemon_id`) across
  canonical, Champions, tournament, and legality data (`dbt/models/normalized/pokemon.sql`
  + `dbt/models/intermediate/`; PokéAPI extraction now covers Mega/regional/
  alternate forms too, and `dbt/seeds/*.csv` hold the controlled OP.GG-,
  MunchStats-, and PokéBase-name-to-PokéAPI-form mappings dataset-spec.md
  calls for)
- [x] Build `pokemon_stat_delta` (canonical vs Champions) outputs
- [x] Generate regulation-aware `legality_snapshot` outputs, sourced from
  PokéBase (`dbt/models/intermediate/int_pokebase_mapped.sql`) instead of
  OP.GG — OP.GG's Champions Pokédex page has only a single
  regulation-agnostic legal pool, so `regulation_code` was permanently
  null there; PokéBase publishes real per-Pokémon regulation-set
  membership (`m-a`/`m-b` as of this snapshot) and closes the gap. This
  table's null-rate gate now passes.
- [x] Normalize `tournament_event`, `tournament_team`, `tournament_team_member`
  (`dbt/models/intermediate/int_munchstats_deduped.sql` also resolves 9
  upstream MunchStats teams that were double-recorded under two placements)
- [x] Once the MunchStats extractor captures tier/record/item fields (see
  Phase 1), add them to `docs/dataset-spec.md`'s entity dictionary —
  `tournament_event` (tier), `tournament_team` (win-rate/`record`),
  `tournament_team_member` (`item`/`ability`/`tera_type`/`moves`) — and
  thread them through the corresponding `dbt/models/normalized/` models
  (new "Optional fields" bullets added to each entity, since MunchStats
  doesn't report tier/record/build for every event/player/slot; the three
  `dbt/tests/singular/assert_null_rate_*` gates were deliberately left
  untouched — they track only the pre-existing required-field lists)

## Phase 3 — Analytics and dashboard outputs

- [x] Publish flat analytical exports and summary aggregates
  (`dbt/models/marts/`: `pokemon_usage_summary`, `legality_summary_by_regulation`,
  `stat_change_leaderboard`, written to `data/marts/*.csv`)
- [x] Provide dashboard-ready trend tables (usage, legality, stat changes)
  (same three marts — `stat_change_leaderboard` currently shows every
  Pokémon as a "gainer" with delta 0, consistent with the zero-stat-delta
  snapshot noted in `releases/manifests/manifest-0.1.0.json`'s
  `known_limitations`, not a bug)
- [x] Document KPI views and filter dimensions (regulation/date/tournament tier)
  (`dbt/models/marts/schema.yml`): regulation and date are available now;
  tournament tier, win-rate proxies, and move/item drill-down (`docs/prd.md`'s
  fuller ambition) need MunchStats extraction fields not captured yet
  (`type`, `record`, `item`/`ability`/`moves` are in the raw source per
  `pipelines/extract/munchstats.py`'s docstring) — documented as a gap
  rather than faked
- [x] Once tier/record/item fields are normalized (see Phase 2), extend
  `dbt/models/marts/` and its `schema.yml` to support tournament-tier
  filtering, win-rate-proxy KPIs, and move/item drill-down, closing the
  gap this section's "Document KPI views and filter dimensions" item
  flagged
  (`pokemon_usage_summary` gained an `event_tier` dimension — one overall
  row per Pokémon plus one row per tier, each ranked within its own
  partition; new marts `pokemon_win_rate_summary` (record_wins/losses-based
  win rate), `pokemon_build_usage` (item x ability usage), and
  `pokemon_move_usage` (unnested move usage) cover the rest. Also fixed a
  pre-existing gap where `pipelines/cli.py`'s `extract` subcommand never
  registered the `pokebase` source, and updated `.gitignore`'s comment to
  match — both silently missed when PokéBase was added in an earlier pass.)

## Phase 4 — Visual assets and card rendering

- [x] Implement extraction contract for Bulbagarden Archives
  (`pipelines/extract/bulbagarden.py`: MediaWiki API pagination + batched
  imageinfo resolution + binary image download to a local gitignored cache,
  no HTML parser dependency needed — see its docstring)
- [x] Fetch the real Bulbagarden Champions-menu-sprites category inventory
  (359 titles) and build the `bulbagarden_title_to_pokeapi_form` mapping
  seed against live PokéAPI data (`dbt/seeds/bulbagarden_title_to_pokeapi_form.csv`
  + `dbt/seeds/schema.yml`); 358/359 titles resolved (one, Mega Meowstic,
  deliberately left unmapped rather than guessed, matching
  `opgg_key_to_pokeapi_form`'s precedent for the identical ambiguity)
- [x] Normalize into the new `pokemon_asset` entity
  (`dbt/models/staging/stg_bulbagarden.sql`,
  `dbt/models/intermediate/int_bulbagarden_mapped.sql` — including the
  cosmetic-duplicate dedup Vivillon/Florges/Furfrou/Alcremie/Pyroar need —
  `dbt/models/normalized/pokemon_asset.sql`); 317 final rows; all four
  release gates (duplicate-key, null-rate, referential-integrity, >=85%
  coverage) pass against real extracted data
- [x] Add PokéAPI-sprites-GitHub type/item icon fetch-on-demand helper
  (`pipelines/render/assets.py`) and a static move-name-to-type reference
  seed (`dbt/seeds/pokeapi_move_types.csv`, all 937 PokéAPI moves) for
  card rendering — neither is a dataset entity or release gate, both are
  rendering-support assets only
- [x] Build the team card renderer (`pipelines/render/`: `data_source.py`
  loads a `CardModel` from either real ingested `tournament_team`/
  `tournament_team_member` data by `team_id` or an ad-hoc JSON build spec;
  `template.py` renders Jinja2 HTML/CSS with base64-inlined sprite/icon
  images; `team_card.py` screenshots it to PNG via Playwright's headless
  Chromium) and a `render-card` CLI subcommand
  (`--team-id <id>` or `--spec <path.json>`, `--output <path.png>`)
- [x] Wire real Bulbagarden sprite art into the renderer end-to-end for a
  team_id pulled from real MunchStats data (ran all five extractors +
  `make dbt-build` for real, then `render-card --team-id
  011yDp6gkk3AeXY6wFCm` — confirmed real sprite art, not placeholder, for
  all 6 roster slots: Sneasler, Kingambit, Aerodactyl, Basculegion,
  Sylveon, Alolan Ninetales)
- [x] Extend `pipelines/release/build.py` to copy `pokemon_asset`-
  referenced images into `releases/data/<version>/images/` and add the
  Bulbagarden source + `pokemon_asset` table + images block to the
  manifest/changelog templates, plus a redistribution-posture disclaimer
  (Bulbagarden-sourced artwork is ultimately Nintendo/Game Freak-owned;
  see `docs/dataset-spec.md`'s "Image asset source" section — the copy
  step, manifest/changelog templates, and `releases/data/README.md`
  disclaimer were already in place; fixed a real gap where a missing
  cached image would crash the release with `FileNotFoundError` instead of
  skipping it gracefully — coverage gate is only >=85%, not 100% —  and
  cut `dataset_version 0.2.0`, the first release with real Bulbagarden
  data: 317 images copied, 0 missing, `pokemon_asset` at 317 rows)

## M6 — Dashboard analytics release

- [x] Stand up a first-party analytics dashboard (KPI overview cards;
  trend views by regulation window and tournament period; drill-down by
  Pokémon, team core, move, and item) on top of `data/marts/*.csv`, per
  `docs/prd.md`'s M6 milestone and "Dashboard analytics module"
  requirement (`pipelines/dashboard/`: KPI cards, usage-by-tier/
  win-rate/build/move drill-downs are functional today against real data;
  the stat-change leaderboard and legal-pool trend-by-regulation sections
  are structurally built but show honest "not enough data yet" empty
  states — driven by `data.py`'s `compute_flags` — since today's snapshot
  has zero nonzero stat deltas and only one `snapshot_date` so far; they'll
  light up automatically as more extractor runs accumulate data)
- [x] Decide and document the dashboard's tech stack and hosting approach
  (resolved in `docs/prd.md`'s Open questions and `docs/dashboard.md`: a
  static HTML/CSS/vanilla-JS site, Chart.js via CDN, no backend, deployed
  via GitHub Pages serving `/docs`)
- [ ] Backlog: build a dynamic Python/Streamlit dashboard on top of
  `pipelines/dashboard/data.py`'s existing mart-loading/KPI logic, once the
  dataset has enough snapshots/trend data (multiple `snapshot_date`s, a
  real Champions rebalance) to justify the added hosting complexity beyond
  today's free static GitHub Pages site — not part of this pass's scope

## Release readiness (v1 definition of done)

All release gates pass as of this writing (see
`reports/validation/validation_report.json`: `release_blocking_findings: []`)
and **`dataset_version 0.1.0` has been published** —
`releases/data/0.1.0/*.csv`, `releases/manifests/manifest-0.1.0.json`,
`releases/changelogs/CHANGELOG-0.1.0.md`.

- [x] Coverage: >=95% of OP.GG legal pool mapped to canonical `pokemon_id`
  (currently 98.4%, 312/317 legal-pool rows)
- [x] Coverage: >=90% of targeted tournament records mapped to normalized team
  tables (currently ~99.9%)
- [x] Coverage: >=95% of PokéBase legal-pool rows mapped to canonical
  `pokemon_id` (currently ~98.7%, 306/310 rows)
- [x] Data quality: required-field null rate <=1% for core tables (all eight
  pass, including `legality_snapshot` now that `regulation_code` is real)
- [x] Data quality: zero duplicate primary-key violations
- [x] Data quality: referential integrity checks pass for Pokémon/team/event
  joins
- [x] Export: versioned CSV outputs for all core entities (`pipelines/release/build.py`,
  `python -m pipelines.cli release --version X.Y.Z`)
- [x] Export: versioned JSON manifest with source lineage and run stats (same
  command; also writes `releases/changelogs/CHANGELOG-<version>.md`)
- [x] Validate example analysis queries (`dbt/analyses/`, see its `README.md`):
  top stat gainers/losers and most-used legal Pokémon both validated with
  real, non-degenerate results; largest legal-pool changes by regulation is
  structurally validated but still currently degenerate for a narrower
  reason now — `regulation_code` is populated, but there's only one
  extraction run (one `snapshot_date`) so far to diff against

## Deferred (post-v1)

See "Deferred sources" in `dataset-spec.md` for the remaining deferred
sources (Limitless VGC, Victory Road) and the rationale for deferring each
one past v1.
