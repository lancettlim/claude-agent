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

The three unchecked `Backlog:` items below are mirrored in `docs/backlog.md`
(items #30, #34, and #31 respectively), alongside the wider post-v1 wish
list. They stay here as the committed record; `backlog.md` holds everything
not yet committed to.

- [x] Stand up a first-party analytics dashboard (KPI overview cards;
  trend views by regulation window and tournament period; drill-down by
  Pokémon, team core, move, and item) on top of `data/marts/*.csv`, per
  `docs/prd.md`'s M6 milestone and "Dashboard analytics module"
  requirement (`pipelines/dashboard/`: KPI cards, usage-by-tier/
  win-rate/build/move drill-downs are functional today against real data)
- [x] Decide and document the dashboard's tech stack and hosting approach
  (resolved in `docs/prd.md`'s Open questions and `docs/dashboard.md`: a
  static HTML/CSS/vanilla-JS site, Chart.js via CDN, no backend, deployed
  via GitHub Pages serving `/docs`)
- [x] Remove the stat-change leaderboard and legal-pool trend-by-regulation
  sections: both were structurally built but permanently showed a
  "not enough data yet" empty state (zero nonzero stat deltas, only one
  `snapshot_date`), so they were cut from `index.html.jinja`/`app.js`
  rather than ship two always-empty sections — see `docs/dashboard.md`'s
  "Removed sections" note; re-add once a rebalance + multiple snapshots
  make the underlying data real
- [x] Dashboard full redesign (live at
  https://lancettlim.github.io/claude-agent/dashboard/): tabbed navigation
  (Overview/Usage/Builds/Moves/Team Cores) replacing the single scrolling
  page; Pokémon sprites, move-type icons, and item icons throughout (KPI
  cards, tables, chart axes, chart tooltips — see `docs/dashboard.md`'s
  "Icon sources"); mobile-responsive layout for the KPI grid, tab nav, and
  tables (breakpoints at 720px/480px, horizontal table scroll); and a new
  `pokemon_team_core_usage` mart + Team Cores drill-down tab, closing the
  "team core" gap named in `docs/prd.md`'s original scope ("Drill-down by
  Pokémon, team core, move, and item usage") but never built until now.
  The stat-change leaderboard and legal-pool-trend sections stay removed
  (still genuinely data-starved, see above) and were not part of this pass.
- [x] Write a UX design system for the dashboard
  (`docs/design-system.md`: design tokens, component catalog, Pokémon-
  representation and naming conventions, ordering conventions) and apply
  it: PascalCase Pokémon display names derived from `pokemon_key`/
  `form_name` instead of the species-only `pokemon_name` column (fixes a
  real bug where alternate forms of one species, e.g. Landorus-Incarnate
  vs. Landorus-Therian, displayed identically —
  `pipelines/dashboard/data.py`'s `to_pascal_case()`, revised from an
  initial camelCase pass); usage-percentage
  (`pokemon_usage_summary.usage_share`) surfaced on the "Most Used" KPI
  card and a new Usage leaders table; explicit descending order-by-usage/
  order-by-win-rate on every Pokémon leaderboard/picker (see
  `docs/design-system.md`'s "Ordering convention"); a new **Speed Tiers**
  tab (bar chart + full table, bucketed into Blazing/Fast/Average/Slow
  badges) built on a new `pokemon_champions_profile` mart (one row per
  legal Pokémon: Champions-format base stats + usage/win-rate); and a new
  **Team Builder** tab (fully client-side, `localStorage`-persisted,
  no backend) for assembling a roster of up to 6 from the legal pool,
  sortable by usage/win-rate/speed, with a speed-order readout reusing
  the Speed Tiers badge scale. Rank badges added to the Usage and Win-rate
  leaders tables for a consistent leaderboard pattern across tabs.
- [x] Backlog: type-effectiveness / head-to-head matchups — **partially
  resolved** by the competitive-UX redesign pass below (new **Matchup**
  tab: type effectiveness + a stats/setup/weather damage calculator, using
  new `pokemon.type_1`/`type_2` and `move_detail` data from PokéAPI). Still
  not buildable: real head-to-head battle-outcome data — MunchStats
  reports team-level win/loss records, not individual battle outcomes
  against a named opponent, so "what beats Pokémon X in practice" has no
  real signal; the Matchup tab's co-usage panel is an explicitly-labeled
  teammate-pairing proxy, not that signal. Closing this for real needs a
  battle-log source not currently in scope or deferred (see
  `docs/design-system.md`'s "Backlog: not yet buildable").
- [x] Broadcast/esports dashboard redesign + feature expansion: full
  visual re-theme (`docs/design-system.md`'s broadcast color-block header,
  `--accent-red`/`--accent-gold` tokens, three-step `--icon-sm/md/lg`
  scale replacing four ad-hoc pixel sizes); removed Chart.js/CDN entirely
  in favor of a dependency-free ranked-list component
  (`renderRankedList()`); merged the Builds/Moves/Team Cores tabs into one
  **Pokémon Profile** tab with a single relevance-sorted picker; Pokémon
  `<select>` dropdowns now sorted by `usage_share` descending instead of
  alphabetically (superseding the prior "dropdowns stay alphabetical"
  convention); sortable `<th>` columns on every leaderboard table
  (resolves the "sortable table columns" backlog item below); new
  **Archetypes** tab (Archetype Explorer) backed by a curated,
  editorial-not-sourced `dbt/seeds/archetype_pokemon_map.csv` seed plus two
  new marts (`pokemon_archetype_usage`, `archetype_summary`); new
  **Regulations** tab (Regulation Comparison) backed by a new
  `cumulative_legal_pokemon_count` column on `legality_summary_by_
  regulation` (naive union across regulations, with the PokéBase
  no-removal-signal caveat shown as visible UI copy — resolves the
  "regulation-code filter" half of the backlog item below); new
  `build_share`/`move_share`/`partner_share` percentage columns on
  `pokemon_build_usage`/`pokemon_move_usage`/`pokemon_team_core_usage` so
  raw counts could be dropped from every view in favor of percentages (a
  small `(n=X)` annotation stays next to win rate specifically, so a
  100%-on-n=1 doesn't read as more authoritative than a well-established
  Pokémon's real win rate); Overview redesigned into a "Top 12" spotlight
  grid + "Top 30" ranked list; a minimum-recorded-matches filter on Win
  rate leaders; `player_name`/`player_country` (real MunchStats fields
  that were previously discarded during extraction, only hashed into an
  opaque `player_id`) now flow through to `tournament_team` and into
  `pipelines/render/`'s `CardModel`; the team-card renderer re-themed to
  match the dashboard's broadcast palette with a player/country banner
  row; and a new **Pro Team Gallery** (curated real teams, pre-rendered
  via `render-card` and committed to `data/reference_teams/`, shown in the
  Team Builder tab with a "Load into my builder" button) — see
  `docs/dashboard.md`'s "Pro Team Gallery", "Cumulative legal pool", and
  "Archetype Explorer" sections.
- [x] Competitive-UX dashboard redesign pass: new PokéAPI extraction
  (`pokemon.type_1`/`type_2`; new `move_detail`/`ability_detail`/
  `item_detail` reference tables, scoped to names seen in real tournament
  rosters) closing the type/move-detail half of the matchup backlog item
  above; new `top_tournament_teams` mart (real MunchStats team leaderboard
  by win_rate); removed the **Archetypes** and **Regulations** tabs
  (`legality_summary_by_regulation` still feeds the page-level Legal Pool
  KPI card, just has no dedicated tab); removed Overview's Top 30 ranked
  list (Top 12 grid only — the Usage tab is the full leaderboard now);
  replaced the ranked-list bar component with a dashboard-wide `.grid-6xn`
  6-column grid (`renderGrid6xn()`) used for every usage/win-rate metric,
  with bolded headline percentages; split the old combined
  `pokemon_build_usage` mart into `pokemon_item_usage`/
  `pokemon_ability_usage`, and gave the Pokémon Profile tab three separate
  Items(top 5)/Ability(top 5)/Moves(top 15) `.grid-6xn` sections instead of
  one combined table, each showing a PokéAPI `short_effect` description; a
  larger `--icon-xl` dual-type badge on the Profile header; new type/role/
  stat-range/usage-range filters (Usage, Speed Tiers, Team Builder); new
  **Matchup** tab (type effectiveness, teammate co-usage, and a damage
  calculator — core mechanics plus a curated item/ability toggle list,
  documented scope in `docs/design-system.md`); new **Top Teams** tab
  (real `top_tournament_teams` leaderboard, the Pro Team Gallery moved
  here from Team Builder, and a pokepast.es-style Showdown-text paste-in/
  out importer/exporter); Team Builder slots now show stats/top-ability/
  top-4-moves per pick, plus an "Export as pokepaste text" button. See
  `docs/design-system.md` for the full component/token reference.
- [ ] Backlog: further dashboard capability items not covered by the above
  redesigns: a tournament-event/date filter once multiple snapshots exist
  (still blocked — only one `snapshot_date` in the data), and trend/line
  charts once that same multi-snapshot data exists
- [ ] Backlog: build a dynamic Python/Streamlit dashboard on top of
  `pipelines/dashboard/data.py`'s existing mart-loading/KPI logic, once the
  dataset has enough snapshots/trend data (multiple `snapshot_date`s, a
  real Champions rebalance) to justify the added hosting complexity beyond
  today's free static GitHub Pages site — not part of this pass's scope

## Foundational enablers (backlog Section 0)

The five items below are mirrored in `docs/backlog.md`'s "Section 0 — Foundational
enablers" (items #1-#5); restating them here per `.claude/loop.md`'s backlog-grooming
loop. Item #1 was the highest-leverage: it unblocked eight other backlog entries.
All five are now shipped.

- [x] Backlog: Append-only staging snapshot history — `pipelines/cli.py`'s
  `extract` subcommand now writes each run to a date-partitioned
  `data/staging/<source>/<date>.csv` (one file per UTC day) instead of the
  extractors overwriting a single file; the extractors themselves (`extract()`
  in each `pipelines/extract/*.py` module) were left untouched since they
  already just write to whatever `output_path` they're given — the
  partitioning lives in the caller. Pruned per source after every write via
  `_RETENTION_COUNTS` (12 weekly PokéAPI snapshots, 14 daily OP.GG/PokéBase,
  7 daily MunchStats given its ~37MB/run size, 10 on-demand Bulbagarden).
  Format stays CSV, not Parquet — matches the existing
  `data/staging/*.schema.json` contracts and needs no new dependency.
  `dbt/models/staging/_sources.yml`'s `external_location` now globs each
  source's directory. `.gitignore` updated to match (`docs/backlog.md` #1)
- [x] Backlog: Snapshot-aware dbt layer — every `dbt/models/staging/stg_*.sql`
  now unions all retained snapshots with a `cast(extracted_at_utc as date) as
  snapshot_date` column (matching `legality_snapshot`'s existing convention),
  making the full extraction history queryable directly from staging. A new
  `dbt/models/intermediate/int_*_latest.sql` selector per source (8 total)
  filters back down to the current point-in-time snapshot; the models that
  used to reference `stg_*` directly (`pokemon`, `pokemon_stat_canonical`,
  `move_detail`, `ability_detail`, `item_detail`, and the four `int_*_mapped`
  models) now reference the corresponding `int_*_latest` model instead — a
  parallel history layer alongside the normalized entities, per the lower-
  disruption option `docs/backlog.md` #2 itself suggested, rather than making
  the normalized layer snapshot-scoped. Verified end-to-end against a
  synthetic two-snapshot PokéAPI fixture (older snapshot with a deliberately
  wrong stat value, newer with the real one): `stg_pokeapi` correctly showed
  both dates, `int_pokeapi_latest` correctly kept only the newer one, and
  `pokemon_stat_canonical.csv` was unaffected — one row per Pokémon, no new
  columns leaked into the normalized CSV output (`docs/backlog.md` #2)
- [x] Backlog: Scheduled refresh automation — new
  `.github/workflows/scheduled-extraction.yml`: daily cron for OP.GG/
  MunchStats/PokéBase, weekly cron for PokéAPI, `workflow_dispatch` for
  ad-hoc runs, Bulbagarden left on-demand-only per its unverified rate-limit
  posture. Since `data/staging/` is intentionally gitignored (see item #1),
  runner-to-runner persistence goes through `actions/cache` (unique key per
  run plus a `restore-keys` prefix fallback, since a cache entry is immutable
  once created) rather than committing snapshots to the repo (`docs/backlog.md` #3)
- [x] Backlog: Plumb `dataset_version` through extraction — new
  `pipelines/versioning.py`'s `latest_published_version()` reads the highest
  version under `releases/manifests/manifest-*.json`; `extract`'s new
  `--dataset-version` flag defaults to it (a routine refresh is staged toward
  a patch bump of the currently-published version unless told otherwise) and
  is threaded through to every extractor call. `pipelines/validate/report.py`'s
  `generate()` uses the same default instead of a hardcoded `"0.1.0"`
  (`docs/backlog.md` #4)
- [x] Backlog: Orchestration entry point — `extract` gained an `all` source
  choice that runs every extractor in dependency order (munchstats before
  pokeapi, so pokeapi's move/ability/item detail fetch has roster names to
  scope to); new Makefile targets `extract-all`, `refresh` (`extract-all` →
  `dbt-build` → `validate`), and `release` (`refresh` → `pipelines.cli
  release`, gated on an explicit `VERSION=X.Y.Z` since picking the next
  dataset version is a human call), chained the same way `dashboard` already
  chains `dbt-build` → `build-dashboard` (`docs/backlog.md` #5)

## Platform hardening (backlog Section 3)

- [x] Backlog #36: Fix vacuously-passing coverage tests — the four
  `dbt/tests/singular/assert_*_coverage.sql` gates (OP.GG legal pool,
  PokéBase legal pool, Bulbagarden sprite, tournament-team-member mapping)
  each had a `when total_count = 0 then 10000` branch that reported 100%
  coverage whenever their source had zero rows, so a total upstream outage
  yielding an empty staging CSV passed every gate and could be released.
  Changed each to report `0` (not `10000`) in that branch instead, so an
  empty source now fails its coverage gate. Confirmed the zero-row branch
  can only be reached by a genuinely empty (but present) snapshot file, not
  a missing one — DuckDB's external-source glob (`_sources.yml`'s
  `external_location`) raises an `IO Error` before the query ever runs if
  no file matches the pattern, verified directly against `duckdb.connect()`
  with a nonexistent vs. an empty (header-only) CSV.
- [x] Backlog #38: Don't swallow the `dbt build` return code —
  `pipelines/cli.py`'s `_run_validate` now captures `dbt build`'s exit code
  instead of discarding it, and treats an exit code outside `{0, 1}` as an
  unexpected crash (returned directly, without generating a report). Even
  for the expected `0`/`1` range, it no longer assumes a `1` means "tests
  ran and some failed" — it now checks that `dbt/target/run_results.json`
  was actually rewritten during this invocation (mtime at or after the
  subprocess call started) before reshaping it into a report, so a compile
  or connection error that exits non-zero without producing fresh results
  is refused rather than silently reshaping a stale prior run's artifacts
  into a false pass. Also switched the subprocess call from bare `dbt` to
  `uv run dbt` to match the Makefile's invocation, and dropped a no-op list
  copy (`[f for f in ...]` -> the list itself). New tests in
  `tests/unit/test_cli.py` cover the clean-pass, gate-failure,
  unexpected-crash-code, and stale-run_results cases.

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
