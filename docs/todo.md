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
  team_id pulled from real MunchStats data (`pipelines/render/data_source.py`'s
  `load_from_team_id` joins `tournament_team_member` to `pokemon_asset` via
  `pokemon_key` and resolves each slot's sprite from the local Bulbagarden
  cache; the ad-hoc JSON spec path remains for teams outside MunchStats's
  coverage)
- [x] Extend `pipelines/release/build.py` to copy `pokemon_asset`-
  referenced images into `releases/data/<version>/images/` and add the
  Bulbagarden source + `pokemon_asset` table + images block to the
  manifest/changelog templates
  (`_copy_referenced_images` copies every `local_cache_path` into
  `releases/data/<version>/images/` and the manifest's `images` block
  records the count; a redistribution-posture disclaimer for
  Nintendo/Game-Freak-owned artwork is still outstanding — see the new
  item below)
- [x] Add a redistribution-posture disclaimer for Bulbagarden-sourced
  artwork to the release manifest/changelog templates and
  `docs/dataset-spec.md`'s "Image asset source" section (split out from
  the item above, which only covered copying the image files themselves)
  (`docs/dataset-spec.md`'s new "Redistribution posture" subsection is the
  source of truth; `pipelines/release/build.py`'s `IMAGE_ATTRIBUTION`
  constant applies it automatically to `manifest.images.attribution` and
  the changelog's "Image attribution" section whenever a release bundles
  at least one image)
- [x] Polish the card template's missing-sprite placeholder and banner
  headline, found while rendering a real `team_id` for the item above:
  the placeholder was a flat gray circle indistinguishable from a loading/
  broken-image state (`pipelines/render/templates/team_card.html.jinja`'s
  `.placeholder` now renders a Poké Ball silhouette instead), and the
  banner showed the raw `team_id` in uppercase (`data_source.py`'s
  `load_from_team_id` now headlines with `Placement #{placement}` when
  available, falling back to `team_id`, with `player_id`/`team_id` moved
  to the subtitle)

## Known gap — legal-pool snapshot vs. tournament history

Discovered while wiring the card renderer against real data (rendering a
real `team_id` showed 5 of 6 slots with no sprite): see
`docs/dataset-spec.md`'s new "Known limitations (living)" section for the
full writeup. OP.GG's current legal-pool snapshot (312 Pokémon) covers
roughly half of the 500 distinct Pokémon MunchStats' tournament history
actually references — not an extraction bug, just OP.GG/Bulbagarden both
reflecting only the *current* format. This silently narrows every Phase 3
mart (all inner-join to `pokemon_stat_champions.is_legal = true`) and
Phase 4 card sprite coverage well beyond what their docs currently imply.

- [ ] Decide how Phase 3 marts should treat roster slots outside the
  current legal-pool snapshot: keep excluding them (and update each
  mart's `schema.yml` description to state the real exclusion rate, not
  just "restricted to the current legal pool"), or loosen the join so
  historical-but-no-longer-legal Pokémon still count toward usage/win-rate
  stats
- [ ] Decide whether `pokemon_asset` should gain a lower-confidence
  fallback path (e.g. PokéAPI's own sprite bundle, already noted as stale
  for the newest Pokémon in `docs/dataset-spec.md`'s "Image asset source"
  section but presumably fine for older/rotated-out ones) for Pokémon
  Bulbagarden's current category doesn't cover, or accept that card
  renders for historical teams will often be partial
- [ ] Add a coverage/validation check comparing the legal-pool snapshot
  against `tournament_team_member`'s distinct Pokémon so this gap is
  visible in `reports/validation/` rather than only discoverable by
  rendering a card and noticing blank sprites

## M6 — Dashboard analytics release

- [x] Decide and document the dashboard's tech stack and hosting approach:
  Streamlit reading `data/marts/*.csv`/`data/normalized/pokemon.csv`
  directly, no new database or backend service (`dashboard/app.py`'s
  module docstring). Public hosting is still undecided — see the new item
  below.
- [x] Stand up a first-party analytics dashboard (KPI overview cards;
  trend views by regulation window and tournament tier; drill-down by
  Pokémon, item/ability, and move) on top of `data/marts/*.csv`, per
  `docs/prd.md`'s M6 milestone and "Dashboard analytics module"
  requirement (`dashboard/app.py`, run via `make dashboard`). "Team core"
  drill-down (per-team roster composition rather than per-Pokémon) isn't
  covered yet — no mart currently aggregates at that grain; team core is
  a new item below. The regulation trend view is currently a single-
  snapshot view rather than a real trend, since only one `snapshot_date`
  has been extracted so far (matches the existing known limitation noted
  for `stat_change_leaderboard`/`legality_summary_by_regulation`).
- [ ] Add a `pokemon_team_core_usage`-style mart (most common multi-
  Pokémon team cores, not just single-Pokémon usage) and wire it into
  `dashboard/app.py`, closing the "team core" drill-down gap noted above
- [ ] Pick and document a public hosting target for the dashboard (e.g.
  Streamlit Community Cloud) once there's a released dataset version
  worth hosting it against; local-only via `make dashboard` for now
- [ ] Add automated test coverage for `dashboard/app.py` (verified
  manually via `streamlit.testing.v1.AppTest` against real local data so
  far, but that needs `data/marts/*.csv`/`data/normalized/*.csv` present,
  which CI doesn't have — see CI's scope note in `CLAUDE.md`)

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
