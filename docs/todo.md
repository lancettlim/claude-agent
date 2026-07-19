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

## M6 — Dashboard analytics release

- [x] Stand up a first-party analytics dashboard (KPI overview cards;
  trend views by regulation window and tournament period; drill-down by
  Pokémon, team core, move, and item) on top of `data/marts/*.csv`, per
  `docs/prd.md`'s M6 milestone and "Dashboard analytics module"
  requirement (added the `pokemon_team_core_usage` mart for the
  team-core drill-down bullet, since no mart covered it yet)
- [x] Decide and document the dashboard's tech stack and hosting approach
  (`docs/prd.md`'s open question) — resolved as **keep both prototypes**,
  each serving a different audience, rather than picking one winner:
  Streamlit (`dashboard/streamlit_app.py`) for internal/exploratory use
  by the data team (fastest to extend, needs a running Python process);
  static HTML (`dashboard/build_static.py`) for shareable public
  snapshots/embedding (zero hosting cost, no process to keep alive, but
  every new view is hand-written JS). See `dashboard/README.md`.
  Still open, deferred until there's an actual deployment need: a real
  hosting target for each (currently both are local-only via `make
  dashboard-streamlit`/`make dashboard-static`) — revisit this doc if
  that changes.

## M6.1 — VGC player-focused dashboard features

Extends M6 with features competitive players specifically asked for:
Pokémon images, a stat-comparison view, speed tiers, and more. PokéAPI's
`/pokemon/{form}` response (already fetched for base stats) turned out to
carry type(s), an official-artwork image URL, and height/weight that the
extractor had never read — capturing them needed no new API calls.

- [x] Capture Pokémon type(s), an official-artwork image URL, and
  height/weight in `pipelines/extract/pokeapi.py`, threaded through
  `dbt/models/normalized/pokemon.sql` as optional fields (kept out of the
  null-rate release gate, matching this layer's existing optional-field
  precedent)
- [x] `pokemon_stat_profile` mart: base stats + type(s) + image per legal
  Pokémon — powers the Speed Tier List and Stat Comparison view
- [x] `pokemon_tera_type_usage` mart: Tera type usage per Pokémon
  (`tournament_team_member.tera_type` was already normalized but no mart
  surfaced it until now)
- [x] `pokemon_ability_usage` mart: ability-only usage per Pokémon (drops
  `pokemon_build_usage`'s item dimension) — powers the Weather/Terrain
  Setters view
- [x] `dashboard/game_data.py`: shared static game-mechanic constants
  (18-type effectiveness chart, type colors, weather/terrain-setting
  ability list) imported by both dashboards, unit-tested in
  `tests/unit/dashboard/test_game_data.py`
- [x] Speed Tier List view (both dashboards): all legal Pokémon by base
  speed, explicitly labeled as Champions-format base speed — no EVs,
  nature, or items modeled, since none of that exists anywhere in this
  dataset
- [x] Stat Comparison ("stats matching") view: pick two Pokémon, compare
  all six stats + BST as paired bars, plus a type-effectiveness readout
  between them
- [x] Speed Control view: Choice Scarf users, Tailwind setters, Trick
  Room setters, each ranked by usage (`pokemon_build_usage`/
  `pokemon_move_usage`, no new extraction)
- [x] Weather/Terrain Setters view: ranked by usage from
  `pokemon_ability_usage`, filtered to the 8 weather/terrain-setting
  abilities
- [x] Meta Tier List view: sortable usage-rank + win-rate table — no
  invented S/A/B/C letter grades, since there's no rigorous basis for one
- [x] Tera type usage added as a 4th Pokémon drill-down column, alongside
  the existing item/ability, move, and team-core columns
- [ ] Full team-builder type-matchup calculator (pick up to 6 Pokémon,
  full weakness/resistance grid vs. an opponent's typing) — same
  `dashboard/game_data.py` type chart, meaningfully more UI/logic;
  deferred from this pass
- [ ] Damage calculator — needs move power/accuracy/category data, not
  captured by any current extractor; would need a new PokéAPI `/move`
  endpoint extraction
- [ ] Real EV/nature-adjusted speed benchmarks — needs a new source;
  already known-deferred per Victory Road's dataset-spec.md rationale
- [ ] Item/move icon sprites — separate PokéAPI endpoints, new extraction
- [ ] Historical trend lines for the new views — blocked on multiple
  extraction snapshot_dates over time, an existing known limitation

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
