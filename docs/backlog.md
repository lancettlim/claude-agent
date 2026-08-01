# Backlog

A wish list of features and improvements for the Pokémon Champions
Competitive Data Platform, kept deliberately broad — moonshots sit next to
afternoon-sized wins, each flagged so the list can be filtered rather than
pre-filtered.

**This is not a commitment.** `docs/todo.md` is the committed checklist:
everything in it is meant to get done. Items here graduate in one direction
only — backlog → todo — once accepted, matching the handoff described in
`.claude/loop.md`'s backlog-grooming loop. `docs/dataset-spec.md` remains the
source of truth for v1 scope; nothing here changes it until it's promoted.

Items are numbered so dependencies can reference each other. **Numbers are
stable and never reused** — a completed or dropped item keeps its number.

## Entry format

- **Size**: `S` an afternoon · `M` a day or two · `L` a week-ish ·
  `XL` a project in its own right
- **Value**: the question it lets you answer, or the failure it prevents
- **Blocked by**: what must be true first — another item, new data, or a new
  source
- **Touches**: the extractor, model, mart, or table it lands in

## The two systemic blockers

Most of the analytics ambition in this repo is gated behind one of two
things. Individual entries below reference these rather than re-explaining
them:

**Blocker A — only one `snapshot_date` has ever existed.** ~~Every extractor
opens its staging CSV with `open(..., "w")`~~ **Fixed by items #1-#3** (all
shipped): `pipelines/cli.py`'s `extract` now writes date-partitioned
snapshots and a `.github/workflows/scheduled-extraction.yml` cron keeps them
accumulating on the cadences `docs/dataset-spec.md` specifies, and
`snapshot_date` is a real, queryable dbt dimension (see Section 0 below for
the full writeup). The blocker's *symptoms* — the degenerate
`dbt/analyses/largest_legal_pool_changes_by_regulation.sql`, the two cut
dashboard sections, every trend view in `docs/prd.md`'s ambition — still
need real multiple-snapshot history to accumulate in production before they
resolve; the engineering blocker is gone, but the calendar time to build up
that history isn't. Item #19 revisits the legal-pool-change query once
enough snapshots exist.

**Blocker B — no Champions rebalance has happened yet.** Every mapped
Pokémon currently has a `stat_total_delta` of exactly `0` (see
`dbt/analyses/README.md`). This is real data, not a bug: the snapshot
predates any balance patch. Nothing in this repo can unblock it — it
resolves when the format changes.

A useful distinction: Blocker A is an engineering problem you can fix today.
Blocker B is a waiting problem. Don't confuse work blocked on one for work
blocked on the other.

---

## Section 0 — Foundational enablers

**All five items in this section are shipped** — see `docs/todo.md`'s
"Foundational enablers (backlog Section 0)" for the implementation writeup.
Entries kept below per "numbers are stable and never reused."

### 1. Append-only staging snapshot history — DONE

- **Size**: XL
- **Value**: The single highest-leverage item in this file. Turns a
  point-in-time dataset into a time series, which is the difference between
  "what is the meta" and "how is the meta changing."
- **Blocked by**: nothing
- **Touches**: `pipelines/cli.py` (the extractors' own `extract()` functions
  didn't need to change — they already just write to whatever `output_path`
  they're given), `data/staging/` layout, `dbt/models/staging/_sources.yml`,
  `.gitignore`

Shipped as date-partitioned `data/staging/<source>/<date>.csv` snapshots,
pruned per source by `pipelines/cli.py`'s `_RETENTION_COUNTS` (12 weekly
PokéAPI, 14 daily OP.GG/PokéBase, 7 daily MunchStats given its ~37MB/run
size, 10 on-demand Bulbagarden). Stayed CSV, not Parquet — matches the
existing schema contracts, no new dependency.

### 2. Snapshot-aware dbt layer — DONE

- **Size**: L
- **Value**: Makes `snapshot_date` a real dimension you can group by rather
  than an incidental column, without which #1's history is inert.
- **Blocked by**: #1
- **Touches**: `dbt/models/staging/`, `dbt/models/intermediate/`,
  `dbt/models/normalized/`, `data/normalized/*.schema.json`

Went with the parallel-history-layer option this entry flagged as less
disruptive: `stg_*.sql` now exposes the full unioned history with
`snapshot_date`, a new `int_*_latest.sql` per source selects the current
point-in-time snapshot, and the normalized layer's primary keys/referential-
integrity tests are untouched. Verified against a synthetic two-snapshot
fixture — see `docs/todo.md` for the walkthrough.

### 3. Scheduled refresh automation — DONE

- **Size**: M
- **Value**: `docs/dataset-spec.md` specifies daily/weekly refresh cadences
  per source that nothing in this repo implements — every snapshot to date
  has been a manual run. Without this, #1 accumulates history only as often
  as you remember to.
- **Blocked by**: nothing (but pairs with #1 — scheduling an overwriting
  extractor accumulates nothing)
- **Touches**: new `.github/workflows/`, `pipelines/cli.py`

Shipped as `.github/workflows/scheduled-extraction.yml`: daily cron for
OP.GG/MunchStats/PokéBase, weekly for PokéAPI. Bulbagarden stays on-demand
per the caveat at `pipelines/extract/bulbagarden.py:39-42` (rate-limiting/
ToS posture for sustained automated access never independently verified).
`data/staging/` being gitignored (see #1) meant runner-to-runner
persistence needed `actions/cache` rather than committing snapshots.

### 4. Plumb `dataset_version` through extraction — DONE

- **Size**: S
- **Value**: Fixes a provenance hole that contradicts the repo's own
  mandatory-provenance convention. Every staging row ever written carries
  `dataset_version = "0.0.0-dev"`.
- **Blocked by**: nothing
- **Touches**: `pipelines/cli.py`, `pipelines/validate/report.py`, new
  `pipelines/versioning.py`

Both defaults now resolve via `pipelines/versioning.py`'s
`latest_published_version()` (highest version under
`releases/manifests/manifest-*.json`) instead of hardcoded placeholders;
`extract` also takes an explicit `--dataset-version` override.

### 5. Orchestration entry point — DONE

- **Size**: S
- **Value**: A full refresh is currently five separate commands plus a build
  plus a validate, in an order you have to remember. Cheap to fix, removes a
  recurring friction and a class of "forgot to re-run X" errors.
- **Blocked by**: nothing
- **Touches**: `pipelines/cli.py`, `Makefile`

`extract all` runs every source in dependency order; new `make extract-all`,
`make refresh` (extract-all → dbt-build → validate), and `make release
VERSION=X.Y.Z` (refresh → release) chain the rest, mirroring `dashboard`'s
existing `dbt-build` → `build-dashboard` chain.

---

## Section 1 — Analytics depth

The main section. Split by what's actually blocking each item, because the
distinction matters more than the feature descriptions do.

### Buildable today — no new data required

These need only SQL and a mart. Every input already exists in the normalized
layer. This is the highest ratio of value to effort in the file.

#### 6. Usage over time from `tournament_event.event_date`

- **Size**: M
- **Value**: Real meta-over-time **without waiting on Blocker A**. Events
  already carry dates spanning the tournament history; usage trends can be
  computed across events rather than across extraction snapshots. This is
  the near-term win hiding in plain sight.
- **Blocked by**: nothing
- **Touches**: new `dbt/models/marts/pokemon_usage_trend.sql`,
  `tournament_event`, `tournament_team_member`

`event_date` is normalized in `tournament_event` and **no mart references
it** — the only mention anywhere in `dbt/models/marts/` is a comment listing
it as an available date dimension (`schema.yml:91`). Note the semantic
difference from snapshot trends: this shows how usage shifted across
tournaments, which is arguably the more interesting axis anyway.

#### 7. Player and country dimension mart

- **Size**: S
- **Value**: Answers "who plays what," "which regions favor which
  archetypes," and "does this player have a signature Pokémon."
- **Blocked by**: nothing
- **Touches**: new mart, `tournament_team`

`player_name` and `player_country` are normalized in `tournament_team` and
never surface in any mart. Related polish: `docs/dashboard.md` notes country
codes render as plain two-letter text because no flag-emoji/ISO lookup
exists yet.

#### 8. Placement-weighted usage

- **Size**: M
- **Value**: Distinguishes "popular" from "successful." Raw usage counts
  treat a last-place team the same as a winning one, which flatters
  crowd-favorite picks and hides quiet top-cut staples.
- **Blocked by**: nothing
- **Touches**: new mart, `tournament_team.placement`,
  `record_wins`/`record_losses`

Consider both a top-cut cutoff view and a continuously weighted one.

#### 9. Team synergy beyond raw co-occurrence

- **Size**: M
- **Value**: `pokemon_team_core_usage` reports how often two Pokémon appear
  together, which mostly just re-ranks the individually popular ones. Lift
  or PMI against expected co-occurrence surfaces genuine pairings — the ones
  that appear together far more than their individual usage predicts.
- **Blocked by**: nothing
- **Touches**: `dbt/models/marts/pokemon_team_core_usage.sql` or a sibling
  mart

Probably the single most interesting analysis in this section. Worth
extending past pairs to triples for real "core" detection.

#### 10. Tera type usage mart

- **Size**: S
- **Value**: Tera type is a defining format mechanic and is entirely absent
  from the analytics layer.
- **Blocked by**: nothing (though see the optional-field caveat at
  `dbt/models/marts/schema.yml:123-127` — coverage is partial)
- **Touches**: new mart, `tournament_team_member.tera_type`

`tera_type` is captured through extraction and normalization, then used by
nothing.

#### 11. Move-type coverage analysis

- **Size**: M
- **Value**: Answers "what types can this team actually hit" and "what's the
  format's offensive coverage profile" — a real teambuilding question.
- **Blocked by**: nothing
- **Touches**: `dbt/seeds/pokeapi_move_types.csv`,
  `dbt/models/marts/pokemon_move_usage.sql`, new mart

The `pokeapi_move_types` seed already holds 937 rows mapping moves to types,
and currently exists only to resolve dashboard icons. Joining it to
`pokemon_move_usage` is nearly free.

#### 12. Usage × regulation cross-tab

- **Size**: S
- **Value**: Usage is currently sliced by `event_tier` but never scoped to a
  regulation, so a Pokémon's usage number silently mixes regulations with
  different legal pools.
- **Blocked by**: nothing
- **Touches**: `dbt/models/marts/pokemon_usage_summary.sql`,
  `legality_snapshot`

#### 13. Win-rate confidence intervals

- **Size**: S
- **Value**: A 100% win rate over 3 recorded matches currently outranks 62%
  over 200. Wilson scoring fixes the ordering and removes an arbitrary
  cutoff.
- **Blocked by**: nothing
- **Touches**: `dbt/models/marts/pokemon_win_rate_summary.sql`,
  `pipelines/dashboard/data.py:169`

The dashboard hardcodes `RECORD_COUNT_FLOOR = 5` as a crude substitute.

#### 14. Item and build concentration metrics

- **Size**: S
- **Value**: Distinguishes Pokémon with one locked-in optimal build from
  ones with genuinely contested item/ability choices — a signal about where
  the metagame is still unsettled.
- **Blocked by**: nothing
- **Touches**: `dbt/models/marts/pokemon_build_usage.sql`

Entropy or a Herfindahl index over `build_share` per Pokémon.

#### 15. Data-derived archetype clustering

- **Size**: L
- **Value**: `archetype_pokemon_map` is a 33-row hand-curated seed and the
  repo's one documented exception to mandatory provenance
  (`dbt/seeds/schema.yml:131-152`). It needs manual upkeep as the meta
  shifts and encodes your opinion rather than the data's. Deriving
  archetypes from real co-occurrence clustering would close the exception.
- **Blocked by**: nothing, though #9 is the natural foundation
- **Touches**: `dbt/seeds/archetype_pokemon_map.csv`,
  `dbt/models/marts/pokemon_archetype_usage.sql`, `archetype_summary.sql`

A softer intermediate step: keep the curated seed but add a test that flags
when its members drift far from observed clusters.

#### 16. Speed-tier bracket mart

- **Size**: M
- **Value**: The Speed Tiers tab currently shows flat base speed. Real speed
  tiers are the modified brackets — +1/+2 stages, Choice Scarf, Tailwind —
  which is what actually determines who moves first.
- **Blocked by**: nothing (pure derivation from existing stats)
- **Touches**: `dbt/models/marts/pokemon_champions_profile.sql`, new mart

Needs EV/nature assumptions to be exact; a documented "max speed investment"
convention is the honest simplification. Item #25 would make it precise.

#### 17. Wire up `stat_change_leaderboard`

- **Size**: S
- **Value**: The mart is built by every `dbt build` and consumed by nothing.
  Either connect it or drop it — a materialized dead-end mart is worse than
  neither.
- **Blocked by**: nothing to wire; **Blocker B** for it to show anything
- **Touches**: `pipelines/dashboard/data.py:29-64`,
  `dbt/models/marts/stat_change_leaderboard.sql`

`MART_FIELDS` lists nine marts; dbt builds ten. Note this only becomes
*visible* work when Blocker B resolves — see #21.

### Blocked on snapshot history (Blocker A)

Items #1-#3 shipped (see Section 0), so the mechanism for this history now
exists — `data/staging/` accumulates real dated snapshots on a schedule. The
items below stay "blocked" in practice, not in mechanism: each needs actual
elapsed time in production for multiple real snapshots to accumulate before
it has non-degenerate data to work with.

#### 18. Meta-shift and movers view

- **Size**: M
- **Value**: "What's rising, what's falling, what's new this week" — the
  headline view of any competitive meta report.
- **Blocked by**: real multi-snapshot history accumulating now that #1-#3 are live
- **Touches**: new mart, `pokemon_usage_summary`

Partially approximable today via #6's event-date axis.

#### 19. Legal-pool change tracking

- **Size**: S once unblocked
- **Value**: Revives an analysis that already exists and has never returned
  a non-degenerate row.
- **Blocked by**: real multi-snapshot history accumulating now that #1-#3 are live
- **Touches**: `dbt/analyses/largest_legal_pool_changes_by_regulation.sql`,
  `dbt/models/marts/legality_summary_by_regulation.sql`

Carries a permanent caveat regardless: PokéBase publishes only positive
legality signals, so absence can't distinguish "banned" from "not yet
observed" (`legality_summary_by_regulation.sql:14-21`). A second source with
explicit ban signals would be the real fix.

#### 20. Restore the legal-pool trend dashboard section

- **Size**: S
- **Value**: The code already existed and was cut for permanently rendering
  an empty state; `docs/dashboard.md` describes re-adding it as "a small,
  self-contained addition" with the removed code recoverable from git
  history.
- **Blocked by**: #19
- **Touches**: `pipelines/dashboard/`, `docs/dashboard/`

### Blocked on a Champions rebalance (Blocker B)

#### 21. Stat-change leaderboard surface

- **Size**: S
- **Value**: The whole `pokemon_stat_delta` entity — a core part of the
  original value proposition, "canonical vs. Champions" — has never shown a
  single nonzero row.
- **Blocked by**: **Blocker B**; #17 for the wiring
- **Touches**: `pipelines/dashboard/`, `docs/design-system.md:32`

The `--positive`/`--positive-bg` design tokens are already reserved for
exactly this. Nothing to do but be ready.

### Needs new provenance — with a sourcing path

Everything here is currently unbuildable from in-scope data. Each entry
names the real path to provenance rather than proposing a hardcoded,
unsourced table — that would violate the mandatory-provenance convention in
`CLAUDE.md`, which is the reason these gaps still exist.

#### 22. `pokemon_type` entity via PokéAPI `/type`

- **Size**: M
- **Value**: The cleanest unblock in this file. Type is the most fundamental
  Pokémon attribute and the dataset does not have it — which is why the
  matchup gap has stayed open. PokéAPI is **already an in-scope source**;
  `/type` is just an endpoint nobody has fetched.
- **Blocked by**: nothing
- **Touches**: `pipelines/extract/pokeapi.py`, new normalized entity,
  `docs/dataset-spec.md` entity dictionary

Adds a tenth core entity, so it's a `MINOR` version bump and a
`dataset-spec.md` update, not just a mart.

#### 23. Type-effectiveness matrix

- **Size**: M
- **Value**: Closes the type half of the long-standing matchup gap recorded
  at `dbt/models/marts/schema.yml:115-121` and in `docs/todo.md`'s M6
  backlog — with real provenance, since PokéAPI publishes
  `damage_relations` per type.
- **Blocked by**: #22
- **Touches**: `pipelines/extract/pokeapi.py`, new normalized entity, new
  mart

Enables defensive/offensive coverage scoring per team, which combined with
#11 is a genuinely strong teambuilding surface.

#### 24. Ability and move metadata from PokéAPI

- **Size**: M
- **Value**: Move power, accuracy, damage class, and ability effects unlock
  damage-calc-style analysis. Today `moves` is a pipe-delimited string of
  names with no properties attached.
- **Blocked by**: nothing (same in-scope source)
- **Touches**: `pipelines/extract/pokeapi.py`, new normalized entities

Note the Champions format rebalances stats; whether it also rebalances moves
is unverified, so canonical move data may need its own Champions-side
counterpart eventually.

#### 25. EV spreads and verified movesets via Victory Road

- **Size**: L
- **Value**: EVs are the missing half of "how is this Pokémon actually
  built." Also fixes MunchStats' ~17% nature coverage
  (`docs/dashboard.md`), and makes #16's speed tiers exact instead of
  assumed.
- **Blocked by**: bringing a deferred source into scope
- **Touches**: new `pipelines/extract/victoryroad.py`, new mapping seed,
  `tournament_team_member`, `docs/data-sources.md`, `docs/dataset-spec.md`

Victory Road's stated deferral reason in `dataset-spec.md` is precisely
this: "defer until detailed moveset/EV enrichment is prioritized." Needs a
Showdown Paste format parser. Un-deferring has precedent — PokéBase was
pulled into v1 the same way once its need became concrete.

#### 26. Historical event coverage via Limitless VGC

- **Size**: XL
- **Value**: Deep historical brackets and player win rates, extending the
  meta history further back than MunchStats reaches.
- **Blocked by**: bringing a deferred source into scope; **no API exists**
- **Touches**: new extractor, `docs/data-sources.md`,
  `docs/dataset-spec.md`

Sized honestly: `docs/data-sources.md` records the extraction method as
manual browser table capture, or contacting Limitless for bulk exports.
There is no scriptable path today, which is the real reason this is XL and
not L. Its deferral reason — "defer until historical event coverage
expansion" — is still accurate.

#### 27. Head-to-head and battle-level matchups

- **Size**: XL
- **Value**: "What beats Pokémon X" is the most-asked competitive question
  the dataset cannot answer, and the other half of the matchup gap #23
  partially closes.
- **Blocked by**: a source that is **neither in scope nor currently
  deferred**
- **Touches**: would require a new source and likely a new entity family

MunchStats reports team-level win/loss records, not per-battle outcomes
against a named opponent, so there is no signal to derive this from. Neither
deferred source supplies it either. Candidate source *types* rather than
named sources: battle-log/replay archives, ladder databases, or
round-by-round pairing data from tournament software. Worth periodically
re-checking whether any has become scriptable — this stays blocked until one
does, and no amount of frontend work substitutes for the missing data.

---

## Section 2 — Consumption surfaces

Deliberately thin: with a single user, query ergonomics matter more than
distribution.

### 28. Local query and notebook quickstart

- **Size**: S
- **Value**: Probably the highest-value consumption item for a single user.
  The DuckDB warehouse at `dbt/data/warehouse.duckdb` already holds every
  model; a short recipe doc plus a few starter queries beats any amount of
  dashboard work for ad-hoc questions.
- **Blocked by**: nothing
- **Touches**: new doc or `notebooks/`, `dbt/analyses/`

### 29. Trend and line charts in the dashboard

- **Size**: M
- **Value**: The trend views `docs/prd.md` describes and the dashboard has
  never been able to show.
- **Blocked by**: real multi-snapshot history accumulating (#1-#3 are live; or #6 for the event-date variant)
- **Touches**: `pipelines/dashboard/templates/`, `static/app.js`

Note the broadcast redesign removed the charting library entirely, so this
means either reintroducing a dependency or extending the dependency-free
ranked-list components.

### 30. Tournament and date filter

- **Size**: S
- **Value**: One of the three open `docs/todo.md` M6 backlog items.
- **Blocked by**: real multi-snapshot history accumulating (#1-#3 are live) or #6
- **Touches**: `pipelines/dashboard/static/app.js`

### 31. Dynamic Streamlit dashboard

- **Size**: L
- **Value**: Mirrors the existing `docs/todo.md` M6 backlog item. Would
  build on `pipelines/dashboard/data.py`'s existing mart-loading and KPI
  logic.
- **Blocked by**: real multi-snapshot history accumulating — the item's own
  stated condition is "once the dataset has enough snapshots/trend data to
  justify the added hosting complexity"; #1-#3 shipped the mechanism, not
  the elapsed time
- **Touches**: new package, `pipelines/dashboard/data.py`

Worth weighing against #28: for a single user, a notebook may deliver most
of the same value with none of the hosting cost.

### 32. JSON feed alongside the baked-in dashboard data

- **Size**: S
- **Value**: Dashboard data is inlined into `index.html` as
  `window.DASHBOARD_DATA` (deliberately, to survive `file://` CORS). A
  sibling `.json` file makes the same data scriptable without re-running
  dbt.
- **Blocked by**: nothing
- **Touches**: `pipelines/dashboard/build.py`

### 33. GitHub Releases with packaged artifacts

- **Size**: S
- **Value**: Consumption today is `git clone` or raw URLs. A zipped release
  package with checksums makes versions citable and verifiable — and
  `releases/` already has everything needed.
- **Blocked by**: nothing (pairs naturally with #35)
- **Touches**: `pipelines/release/build.py`, `.github/workflows/`

### 34. Pokémon Profile empty state

- **Size**: S
- **Value**: The third open `docs/todo.md` M6 backlog item.
- **Blocked by**: nothing
- **Touches**: `pipelines/dashboard/static/app.js`

The existing item notes the current behavior — defaulting to the
highest-usage Pokémon — may actually be preferable to an empty state.
Decide before building.

---

## Section 3 — Platform, quality, and ops

Separated from the analytics list so it doesn't dilute it. These are
verified gaps, not speculative hardening. Items #36 and #38 are the two with
real correctness consequences.

### 35. CI workflow

- **Size**: M
- **Value**: `make check` (lint + test + dbt build + validate) exists and
  nothing runs it automatically. There is no `.github/` directory at all.
- **Blocked by**: nothing
- **Touches**: new `.github/workflows/`

### 36. Fix vacuously-passing coverage tests

- **Size**: S
- **Value**: A correctness hole in the release gate. All four
  `assert_*_coverage.sql` tests return `10000` bps (100%) when the source
  has zero rows — so a total upstream outage that yields an empty CSV
  **passes every gate and can be released**.
- **Blocked by**: nothing
- **Touches**: `dbt/tests/singular/assert_*_coverage.sql`

The comments explain the intent honestly ("vacuously not failed (pending
Phase 1 extraction)") — it was scaffolding for a pre-extraction repo and has
outlived its reason. Pairs with #40.

### 37. Derive the validation report from dbt's manifest

- **Size**: M
- **Value**: `pipelines/validate/report.py` maps tests via four hardcoded
  dicts covering 30 of dbt's 32 singular tests. Two —
  `assert_archetype_pokemon_map_resolves_to_pokemon` and
  `assert_duplicate_key_archetype_pokemon_map` — run on every build but
  appear in no report section, so they **can never block a release**. Any
  new test is invisible to the gate until someone remembers to edit
  `report.py`.
- **Blocked by**: nothing
- **Touches**: `pipelines/validate/report.py`,
  `reports/validation/validation_report.template.json`

### 38. Don't swallow the `dbt build` return code — DONE

- **Size**: S
- **Value**: The other correctness hole. `subprocess.run(["dbt", "build"])`
  at `pipelines/cli.py:46` discards its exit status. The comment correctly
  justifies this for *test* failures, but a compile or connection error also
  exits non-zero **without writing fresh `run_results.json`** — so
  `validate` silently reshapes the previous run's artifacts and can report a
  pass on a build that never ran.
- **Blocked by**: nothing
- **Touches**: `pipelines/cli.py:41-52`

`_run_validate` now captures the exit code, treats anything outside
`{0, 1}` as a crash it returns directly (no report generated), and — even
within `{0, 1}` — refuses to reshape `run_results.json` unless its mtime
shows it was actually rewritten by this invocation, catching the compile/
connection-error case the ratio-based gates couldn't see. Also fixed the two
nits noted here: the subprocess call is now `uv run dbt build` (matches the
Makefile), and the no-op list copy is gone. See `docs/todo.md`'s "Platform
hardening" section.

### 39. Source freshness gate

- **Size**: S
- **Value**: Nothing checks whether a snapshot is stale. The pipeline will
  happily validate and release six-month-old data with every gate green.
- **Blocked by**: nothing
- **Touches**: `dbt/models/staging/_sources.yml`,
  `pipelines/validate/report.py`

No `loaded_at_field` or `freshness:` block is configured anywhere, though
every row already carries `extracted_at_utc`.

### 40. Row-count anomaly detection

- **Size**: M
- **Value**: Every current gate is a ratio or a duplicate count, so a source
  silently dropping from 106,000 rows to 500 passes all of them. Volume
  baselines catch the partial-outage case that #36 catches only in the total
  case.
- **Blocked by**: nothing, though #1's history makes baselines far easier
- **Touches**: `dbt/tests/singular/`, `pipelines/validate/report.py`

### 41. Schema-drift enforcement

- **Size**: M
- **Value**: The `data/staging/*.schema.json` and `data/normalized/*.schema.json`
  contracts are described as the durable tracked contract for each source —
  but they are documentation only. **No code loads or asserts against
  them**, and every `stg_*` model is a bare `select *`, so an upstream
  column rename propagates silently or surfaces as a confusing downstream
  error.
- **Blocked by**: nothing
- **Touches**: `data/**/*.schema.json`, `dbt/models/staging/`, `tests/`

Especially worth it given both RSC-scraping extractors depend on hand-rolled
string markers (`pipelines/extract/opgg.py:65`) that will break silently on
any upstream markup change.

### 42. Mart tests

- **Size**: M
- **Value**: All 32 singular tests target normalized and seed models. **Zero
  tests exist on any of the ten marts** — the layer the dashboard actually
  reads.
- **Blocked by**: nothing
- **Touches**: `dbt/tests/singular/`, `dbt/models/marts/schema.yml`

Also worth noting there is not a single dbt *generic* test in the project —
no `unique`, `not_null`, `relationships`, or `accepted_values` anywhere.
Everything is bespoke SQL, which is a lot of surface for tests that generics
would cover in one line.

### 43. Extractor resilience

- **Size**: M
- **Value**: No retry, backoff, or rate limiting anywhere. `pokeapi.py`
  fires roughly 1,350 sequential unthrottled requests and a single
  `raise_for_status()` anywhere aborts the run with no output at all.
  Becomes materially more important once #3 runs extraction unattended.
- **Blocked by**: nothing
- **Touches**: all five `pipelines/extract/*.py`

### 44. Incremental extraction

- **Size**: M
- **Value**: MunchStats refetches all 31 tournaments and ~106k rows every
  run even though historical events never change. Wasteful now, actively
  painful under #3's scheduled cadence.
- **Blocked by**: nothing (design alongside #1)
- **Touches**: `pipelines/extract/munchstats.py`, others as applicable

Bulbagarden's sha1-based `skip_existing` is the existing pattern to follow.
Conditional requests (ETag / If-Modified-Since) would help the two scraped
sources.

### 45. `pipelines/cli.py` test coverage

- **Size**: S
- **Value**: 74 unit tests cover the extractors, release, render, dashboard,
  and validation modules. The CLI — the only entry point to all of them —
  has **zero tests**. Argument parsing, subcommand dispatch, and both
  exit-code paths are entirely unexercised.
- **Blocked by**: nothing
- **Touches**: new `tests/unit/test_cli.py`

Related: there is no `conftest.py` or shared fixture module anywhere under
`tests/`, so each file re-declares its own helpers.

### 46. Dashboard JS duplication check

- **Size**: S
- **Value**: `pipelines/dashboard/static/app.js` and the committed
  `docs/dashboard/app.js` are byte-identical copies with nothing enforcing
  it. Editing the wrong one produces a published site that silently
  disagrees with its source.
- **Blocked by**: nothing
- **Touches**: `tests/`, or a `make` target

### 47. `sprites.py` rebuild ordering constraint

- **Size**: S
- **Value**: `copy_sprites` deliberately `rmtree`s the output `images/`
  directory (`pipelines/dashboard/sprites.py:58-61`) to stop stale sprites
  accumulating — reasonable in isolation, but it means any asset written to
  `images/` *before* it in a build gets wiped. Today's call order happens to
  be safe; nothing guarantees it stays that way.
- **Blocked by**: nothing
- **Touches**: `pipelines/dashboard/sprites.py`, `build.py`

Prune stale files by name rather than nuking the directory, or make the
ordering constraint explicit and tested.

### 48. Extraction run metadata and structured logging

- **Size**: M
- **Value**: `reports/validation/extraction_summary.json` reports per-source
  request success rates and row counts — and is a **hand-written static
  file dated 2026-07-19** that no code generates. There is no run history,
  no structured logging, and failures surface only as an unhandled
  traceback.
- **Blocked by**: nothing
- **Touches**: `pipelines/extract/`, `reports/validation/`

Prerequisite for any real monitoring, and directly supports #40's baselines.

---

## Section 4 — Known documentation debt

Not full backlog entries — these are drift and belong to `.claude/loop.md`'s
tech-debt loop, listed here only so they're written down somewhere.

- `docs/prd.md` still names Chart.js as the resolved dashboard stack; the
  broadcast redesign removed the charting library entirely
  (`docs/dashboard.md`).
- `docs/todo.md`'s release-readiness header says `0.1.0` is the published
  version; `CLAUDE.md` and `README.md` say `0.2.0`.
- `docs/todo.md`'s null-rate item says "all eight" core tables pass; there
  are nine since `pokemon_asset` was added in Phase 4.
- `docs/dataset-spec.md`'s trailing "Next implementation task" section
  describes repository scaffolding completed long ago.
- `dbt/analyses/README.md` still attributes the degenerate legal-pool query
  to OP.GG's null `regulation_code`; PokéBase resolved that, and the real
  reason is now Blocker A.
- `.claude/loop.md`'s "Why a loop" section claims "Phase 1+ ingestion/
  normalization logic is still unwritten."
- `docs/design-system.md:415-416` has a sentence mangled mid-edit ("...a
  battle-log source neither currently in scope nor deferred source... is
  confirmed to provide").
- `docs/dataset-spec.md`'s phased roadmap names only three phases; Phase 4
  and M6 exist only in `docs/todo.md`.

One item on this list is **not** prose drift and deserves separate
attention: `releases/manifests/manifest-0.2.0.json` has
`"known_limitations": []`, while all three limitations recorded in
`manifest-0.1.0.json` — PokéBase's missing removal signal, the all-zero stat
deltas, and the three excluded ambiguous form mappings — remain true in
0.2.0. That is a published-artifact regression, not a doc nit.
