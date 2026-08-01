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

## Progress overview

*Last updated 2026-08-01.* 49 numbered items exist (#1-#49, none dropped).
This table is maintained by hand alongside each grooming/implementation
pass — if it drifts from the per-item statuses below, the per-item entries
are the source of truth.

| Status | Count | Meaning |
|---|---|---|
| **Done** | 29 | Shipped and verified against real data: #1-#6, #8-#14, #22-#24, #28, #29, #30, #32, #33, #35, #36, #37, #38, #39, #40, #46, #47 |
| **Partially done** | 2 | Real progress, real gap remains: #7 (team-grain, not player/country-grain), #45 (CLI's `extract`/`validate` paths covered, `release`/`render-card`/`build-dashboard` dispatch isn't) |
| **Resolved, no build needed** | 2 | #17 — deliberately left unwired, not an oversight; #34 — current default-to-highest-usage behavior decided to be correct as-is; see each entry |
| **Open, buildable now** | 8 | No blocker, just not started: #15, #16, #41, #42, #43, #44, #48, #49 |
| **Blocked** | 8 | Waiting on Blocker A (#18-#20), Blocker B (#21), a source that's deferred/out-of-scope/nonexistent (#25-#27), or snapshot history accumulating (#31) |

By section:

| Section | Done | Partial/Resolved | Open | Blocked | Total |
|---|---|---|---|---|---|
| 0 — Foundational enablers | 5 | 0 | 0 | 0 | 5 |
| 1 — Buildable today (#6-#17) | 8 | 2 | 2 | 0 | 12 |
| 1 — Blocked on Blocker A (#18-#20) | 0 | 0 | 0 | 3 | 3 |
| 1 — Blocked on Blocker B (#21) | 0 | 0 | 0 | 1 | 1 |
| 1 — Needs new provenance (#22-#27) | 3 | 0 | 0 | 3 | 6 |
| 2 — Consumption surfaces (#28-#34) | 5 | 1 | 0 | 1 | 7 |
| 3 — Platform, quality, and ops (#35-#49) | 8 | 1 | 6 | 0 | 15 |
| **Total** | **29** | **4** | **8** | **8** | **49** |

Takeaways: every item in Section 0 and every "buildable today, no new data
required" item that isn't genuinely open (#15, #16) or a judgment call
(#17) is done — that bucket is close to exhausted. Section 2 (Consumption
surfaces) is now fully closed out except the one genuinely blocked item
(#31). This pass closed four more items (#29, #30, #33, #40) and added
one new, precisely-scoped item (#49 — a real correctness gap in the
validation report's bps-based metrics, discovered while verifying #29/#30
against a real data run, not shipped-but-hidden). The remaining open work
now skews toward Section 3 (platform/quality hardening, 6 open items:
#41-#44, #48, #49). The 8 blocked items aren't neglect — 4 are waiting on
real-world time/events (Blocker A's snapshot history, Blocker B's
rebalance, #31's snapshot-dependent hosting justification) and 4 need a
source this repo doesn't have and, in
#26/#27's case, may not exist in scriptable form at all.

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

#### 6. Usage over time from `tournament_event.event_date` — DONE

- **Size**: M
- **Value**: Real meta-over-time **without waiting on Blocker A**. Events
  already carry dates spanning the tournament history; usage trends can be
  computed across events rather than across extraction snapshots. This is
  the near-term win hiding in plain sight.
- **Blocked by**: nothing
- **Touches**: new `dbt/models/marts/pokemon_usage_trend.sql`,
  `tournament_event`, `tournament_team_member`

Shipped as `dbt/models/marts/pokemon_usage_by_event_date.sql` (named to
match its grain rather than the originally-proposed `pokemon_usage_trend`):
usage count/share/rank per Pokémon x event_date, partitioned by
event_date. Verified against real data: 2,073 rows across the real
MunchStats event-date history. Not yet wired into the dashboard UI (#29's
trend/line charts are the natural consumer, but that item is bigger scope
than this mart alone).

#### 7. Player and country dimension mart — PARTIALLY DONE

- **Size**: S
- **Value**: Answers "who plays what," "which regions favor which
  archetypes," and "does this player have a signature Pokémon."
- **Blocked by**: nothing
- **Touches**: new mart, `tournament_team`

`player_name`/`player_country` now surface in `top_tournament_teams`
(`dbt/models/marts/top_tournament_teams.sql`, shipped as part of the M6
Top Teams tab work), answering "who plays what" for the top 100 teams by
win rate. Still open: a dedicated country/player-aggregate dimension mart
("which regions favor which archetypes," "does this player have a
signature Pokémon" across their full history rather than one team row) —
`top_tournament_teams` is team-grain, not player- or country-grain.
Related polish still open too: `docs/dashboard.md` notes country codes
render as plain two-letter text because no flag-emoji/ISO lookup exists.

#### 8. Placement-weighted usage — DONE

- **Size**: M
- **Value**: Distinguishes "popular" from "successful." Raw usage counts
  treat a last-place team the same as a winning one, which flatters
  crowd-favorite picks and hides quiet top-cut staples.
- **Blocked by**: nothing
- **Touches**: new mart, `tournament_team.placement`,
  `record_wins`/`record_losses`

Shipped as `dbt/models/marts/pokemon_placement_weighted_usage.sql`: both
views this entry asked for. `top_cut_usage_count`/`top_cut_usage_share`
use a hard top-8 cutoff (the standard VGC/Champions bracket size);
`placement_weighted_score`/`weighted_usage_share` use a continuous
inverse-placement (`1/placement`) weight per appearance instead, so a
1st-place finish counts far more than a 200th with no cutoff
discontinuity. Not yet wired into the dashboard UI — the mart is real,
queryable output (verified against real MunchStats data: Incineroar leads
both views), but surfacing it as a dashboard tab/section is separate,
undone follow-up work.

#### 9. Team synergy beyond raw co-occurrence — DONE (pairs; triples still open)

- **Size**: M
- **Value**: `pokemon_team_core_usage` reports how often two Pokémon appear
  together, which mostly just re-ranks the individually popular ones. Lift
  or PMI against expected co-occurrence surfaces genuine pairings — the ones
  that appear together far more than their individual usage predicts.
- **Blocked by**: nothing
- **Touches**: `dbt/models/marts/pokemon_team_core_usage.sql` or a sibling
  mart

Shipped as a sibling mart, `dbt/models/marts/pokemon_team_synergy.sql`,
built on top of `pokemon_team_core_usage`'s already-mirrored pairs: lift
per pair (`P(A,B) / (P(A) x P(B))`, using distinct-team membership as the
probability space), with `pair_team_count` exposed alongside it since lift
is noisy at low pair counts. Verified against real data: 10,336 pair rows;
spot-checked Incineroar's top partners by lift (Vileplume, Slowking,
Steelix, Hawlucha-Mega, Sceptile) against its top partners by raw
co-occurrence and confirmed they're a different, less-generically-popular
set, as intended. Still open: extending past pairs to triples for real
"core" detection, as this entry originally suggested — a bigger
combinatorial problem than the pairwise case, left for a follow-up.

#### 10. Tera type usage mart — DONE

- **Size**: S
- **Value**: Tera type is a defining format mechanic and is entirely absent
  from the analytics layer.
- **Blocked by**: nothing (though see the optional-field caveat at
  `dbt/models/marts/schema.yml:123-127` — coverage is partial)
- **Touches**: new mart, `tournament_team_member.tera_type`

Shipped as `dbt/models/marts/pokemon_tera_type_usage.sql`, mirroring
`pokemon_item_usage`/`pokemon_ability_usage`'s share-of-own-total pattern.
Not yet wired into the dashboard UI (real, queryable mart output; a Tera
Types drill-down section is separate, undone follow-up work).

#### 11. Move-type coverage analysis — SUPERSEDED, mostly resolved

- **Size**: M
- **Value**: Answers "what types can this team actually hit" and "what's the
  format's offensive coverage profile" — a real teambuilding question.
- **Blocked by**: nothing
- **Touches**: `dbt/seeds/pokeapi_move_types.csv`,
  `dbt/models/marts/pokemon_move_usage.sql`, new mart

This entry's originally-described path (`pokeapi_move_types` seed ->
`pokemon_move_usage`) shipped, and then went further: `pokemon_move_usage`
now joins real PokéAPI `move_detail` (not the static seed) for
`move_type`/`power`/`accuracy`/`category`/`priority`/`pp` per move, and the
dashboard's Matchup tab computes real type effectiveness and a
stats/setup/weather-aware damage calculator client-side from it (see the
Competitive-UX redesign pass in `docs/todo.md`'s M6 section). What's
genuinely still open, and belongs to backlog #23/#27 rather than here: a
*team-level* offensive coverage score (e.g. "what fraction of types can
this specific 6-Pokémon team hit super-effectively") — today's Matchup tab
answers per-move/per-Pokémon matchups, not a precomputed team-composition
coverage metric.

#### 12. Usage × regulation cross-tab — DONE

- **Size**: S
- **Value**: Usage is currently sliced by `event_tier` but never scoped to a
  regulation, so a Pokémon's usage number silently mixes regulations with
  different legal pools.
- **Blocked by**: nothing
- **Touches**: `dbt/models/marts/pokemon_usage_summary.sql`,
  `legality_snapshot`

Shipped as a new sibling mart, `dbt/models/marts/pokemon_usage_by_
regulation.sql`, rather than a modification to `pokemon_usage_summary`
itself: `tournament_event` carries no `regulation_code` of its own (no
temporal "usage during regulation X" signal exists to slice by), so this
cross-joins the existing overall `usage_count` against
`legality_snapshot`'s regulation membership at the latest `snapshot_date`,
with `usage_share`/`usage_rank` recomputed within each `regulation_code`
partition. Not yet wired into the dashboard UI.

#### 13. Win-rate confidence intervals — DONE

- **Size**: S
- **Value**: A 100% win rate over 3 recorded matches currently outranks 62%
  over 200. Wilson scoring fixes the ordering and removes an arbitrary
  cutoff.
- **Blocked by**: nothing
- **Touches**: `dbt/models/marts/pokemon_win_rate_summary.sql`,
  `pipelines/dashboard/data.py:169`

`pokemon_win_rate_summary.sql` now computes `wilson_lower_bound` (a 95%
Wilson score confidence interval lower bound) and `wilson_rank` per
Pokémon; `pipelines/dashboard/data.py`'s `compute_kpis` now picks the KPI
card's `top_win_rate_pokemon` by `wilson_rank` instead of the old
`RECORD_COUNT_FLOOR = 5` filter-then-max-by-`win_rate` heuristic, which is
now removed. Verified against real data: the old logic's top pick was
Victreebel-Mega at 63% over 3 matches; the new logic correctly picks
Kingambit at 50.6% over 2,384 matches. The Usage tab's Win rate leaders
table still uses its own user-selectable min-record-count filter
(unrelated UI control, left as-is) — only the KPI card's single "top"
pick and the underlying mart changed.

#### 14. Item and build concentration metrics — DONE

- **Size**: S
- **Value**: Distinguishes Pokémon with one locked-in optimal build from
  ones with genuinely contested item/ability choices — a signal about where
  the metagame is still unsettled.
- **Blocked by**: nothing
- **Touches**: `dbt/models/marts/pokemon_build_usage.sql`

`pokemon_build_usage` itself no longer exists (split into
`pokemon_item_usage`/`pokemon_ability_usage` by the M6 broadcast redesign,
before this item was picked up). Shipped as a new sibling mart,
`dbt/models/marts/pokemon_build_concentration.sql`: a Herfindahl-Hirschman
Index (sum of squared shares) over each of `pokemon_item_usage.item_share`
and `pokemon_ability_usage.ability_share` per Pokémon, plus how many
distinct items/abilities were observed at all. Not yet wired into the
dashboard UI.

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

#### 17. Wire up `stat_change_leaderboard` — RESOLVED, staying unwired on purpose

- **Size**: S
- **Value**: The mart is built by every `dbt build` and consumed by nothing.
  Either connect it or drop it — a materialized dead-end mart is worse than
  neither.
- **Blocked by**: nothing to wire; **Blocker B** for it to show anything
- **Touches**: `pipelines/dashboard/data.py:29-64`,
  `dbt/models/marts/stat_change_leaderboard.sql`

This entry's "connect it or drop it" framing predates a decision that
already answers it: `docs/todo.md`'s M6 section records that a stat-change
leaderboard dashboard section was built, then deliberately **removed**
(see `docs/dashboard.md`'s "Removed sections" note) specifically because
Blocker B makes every row a `stat_total_delta` of 0 — a permanently empty
state is worse than no section. So the mart stays deliberately unwired,
not accidentally: recorded here so it doesn't read as an open gap.
Revisit only alongside #21, when Blocker B actually resolves.

Mart-count note, corrected: `MART_FIELDS` lists nine marts; `dbt build`
now produces fifteen (five shipped by this pass — #8, #10, #12, #14, plus
`pokemon_win_rate_summary`'s new Wilson columns — landed as new marts not
wired into `MART_FIELDS` either, for the same "real output, dashboard
surfacing is separate work" reason, not the Blocker-B reason this item
covers).

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

#### 22. `pokemon_type` entity via PokéAPI `/type` — DONE, via a lighter path

- **Size**: M
- **Value**: The cleanest unblock in this file. Type is the most fundamental
  Pokémon attribute and the dataset does not have it — which is why the
  matchup gap has stayed open. PokéAPI is **already an in-scope source**;
  `/type` is just an endpoint nobody has fetched.
- **Blocked by**: nothing
- **Touches**: `pipelines/extract/pokeapi.py`, new normalized entity,
  `docs/dataset-spec.md` entity dictionary

Shipped by the Competitive-UX redesign pass (`docs/todo.md`'s M6 section),
via a lighter path than this entry proposed: `type_1`/`type_2` landed as
new columns on the existing `pokemon` entity (real PokéAPI data, full
provenance) rather than a standalone `pokemon_type` dimension entity — no
`MINOR` version bump needed, since it extended an existing entity instead
of adding a tenth one. `docs/dataset-spec.md`'s entity dictionary already
documents `pokemon.type_1`/`type_2`, so that update isn't owed either.

#### 23. Type-effectiveness matrix — DONE, via a lighter path

- **Size**: M
- **Value**: Closes the type half of the long-standing matchup gap recorded
  at `dbt/models/marts/schema.yml:115-121` and in `docs/todo.md`'s M6
  backlog — with real provenance, since PokéAPI publishes
  `damage_relations` per type.
- **Blocked by**: #22
- **Touches**: `pipelines/extract/pokeapi.py`, new normalized entity, new
  mart

Shipped as a client-side `TYPE_CHART` constant in
`pipelines/dashboard/static/matchup.js`, not a new normalized entity/mart
fed by PokéAPI's `damage_relations` as originally proposed. Deliberate,
documented divergence, not a provenance shortcut: type effectiveness is a
fixed game-mechanics fact, not a per-record extracted fact, so it gets the
same treatment `pokemon_champions_profile`'s schema.yml entry already
gives `app.js`'s `SPEED_TIERS` bucketing constant and weather-boost
multipliers. Powers the Matchup tab's type-effectiveness view and damage
calculator against real `pokemon.type_1`/`type_2` and `move_detail` data.
Still the real open half of the matchup gap, unrelated to this item: real
head-to-head battle-outcome data (#27) — no source provides it.

#### 24. Ability and move metadata from PokéAPI — DONE

- **Size**: M
- **Value**: Move power, accuracy, damage class, and ability effects unlock
  damage-calc-style analysis. Today `moves` is a pipe-delimited string of
  names with no properties attached.
- **Blocked by**: nothing (same in-scope source)
- **Touches**: `pipelines/extract/pokeapi.py`, new normalized entities

Shipped exactly as described, by the Competitive-UX redesign pass: three
new normalized entities with real PokéAPI provenance —
`dbt/models/normalized/move_detail.sql` (type/power/accuracy/category/
priority/pp/short_effect), `ability_detail.sql`, and `item_detail.sql` —
scoped to names actually seen in real tournament rosters rather than
PokéAPI's full catalog. All three are documented in `docs/dataset-spec.md`'s
entity dictionary and joined into `pokemon_move_usage`/
`pokemon_ability_usage`/`pokemon_item_usage`. The Champions-move-rebalance
question this entry flagged is still unresolved, but unverifiable from any
in-scope source, not a gap in this item's own scope.

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

### 28. Local query and notebook quickstart — DONE

- **Size**: S
- **Value**: Probably the highest-value consumption item for a single user.
  The DuckDB warehouse at `dbt/data/warehouse.duckdb` already holds every
  model; a short recipe doc plus a few starter queries beats any amount of
  dashboard work for ad-hoc questions.
- **Blocked by**: nothing
- **Touches**: new doc or `notebooks/`, `dbt/analyses/`

Shipped as `docs/local-queries.md`: how to open the warehouse (DuckDB CLI or
Python, both from `dbt/`, since external tables resolve paths relative to
that working directory), how to list every queryable table, and seven
starter queries — each run against a real, freshly-extracted snapshot to
confirm non-degenerate output, not just checked for syntax. Several of the
queries (tera type usage, team synergy lift, placement-weighted usage,
build concentration) surface marts that still aren't wired into the
dashboard UI at all, so this doc is currently the only way to see their
output.

### 29. Trend and line charts in the dashboard — DONE, event-date variant

- **Size**: M
- **Value**: The trend views `docs/prd.md` describes and the dashboard has
  never been able to show.
- **Blocked by**: ~~real multi-snapshot history accumulating (#1-#3 are
  live; or #6 for the event-date variant)~~ #6 shipped
  `pokemon_usage_by_event_date`, so the event-date variant's data
  dependency is resolved — this item is no longer blocked, just not yet
  built. The snapshot-date variant still needs #1-#3's history to actually
  accumulate multiple snapshots in production.
- **Touches**: `pipelines/dashboard/templates/`, `static/app.js`

Note the broadcast redesign removed the charting library entirely, so this
means either reintroducing a dependency or extending the dependency-free
ranked-list components.

Shipped the event-date variant as the Usage tab's new **Trends** subtab
(combined with #30 below, since both landed in the same date-filtered
view): took the "extend the dependency-free components" branch rather
than reintroducing a charting dependency, per this entry's own note. Each
Pokémon's row shows its `usage_share` *change* versus the immediately
preceding tournament date (not a fixed time window) as a colored `▲/▼
Npp` badge, or a `NEW` badge for a Pokémon absent from that previous
date — new `.badge-positive`/`.badge-negative`/`.badge-new` variants
reusing the already-defined `--positive`/`--danger`/`--warning` tokens (no
new color pair needed). A Pokémon on the *very first* tournament date on
record shows neither (no prior date exists at all, a different case from
a specific Pokémon being new) — see `docs/design-system.md`'s new "Trend
delta badge" entry. Verified against a real `extract all` + `dbt build` +
`build-dashboard` run: 26 real tournament dates, correct deltas/NEW badges
at a mid-range date, and all "—" (no false NEW badges) at the earliest
date, with zero browser console errors. The snapshot-date variant (real
multi-extraction history, not tournament dates) is still open, gated on
Blocker A's elapsed time as before.

### 30. Tournament and date filter — DONE

- **Size**: S
- **Value**: One of the three open `docs/todo.md` M6 backlog items.
- **Blocked by**: ~~real multi-snapshot history accumulating (#1-#3 are
  live) or #6~~ #6 shipped; a real `event_date` dimension exists to filter
  by now (`pokemon_usage_by_event_date`). Not yet built.
- **Touches**: `pipelines/dashboard/static/app.js`

Shipped as `#usage-trend-date-filter` in the same Trends subtab #29 added:
a plain `<select>` of every distinct `pokemon_usage_by_event_date.
event_date`, most recent first and selected by default. Deliberately not
routed through the shared `fillSelect()` helper (which always prepends an
"All" option) — an unfiltered/all-dates view doesn't mean anything for a
per-date usage snapshot, so the select only ever offers real dates.

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

### 32. JSON feed alongside the baked-in dashboard data — DONE

- **Size**: S
- **Value**: Dashboard data is inlined into `index.html` as
  `window.DASHBOARD_DATA` (deliberately, to survive `file://` CORS). A
  sibling `.json` file makes the same data scriptable without re-running
  dbt.
- **Blocked by**: nothing
- **Touches**: `pipelines/dashboard/build.py`

`build()` now also writes `data.json` (the exact same payload
`json.dumps`'d, not reparsed from the escaped inline script) alongside
`index.html`. `index.html` stays the inline-data version — not switched to
`fetch()`-ing `data.json` — so it keeps working opened directly via
`file://`, per this module's own docstring.

### 33. GitHub Releases with packaged artifacts — DONE

- **Size**: S
- **Value**: Consumption today is `git clone` or raw URLs. A zipped release
  package with checksums makes versions citable and verifiable — and
  `releases/` already has everything needed.
- **Blocked by**: nothing (pairs naturally with #35)
- **Touches**: `pipelines/release/build.py`, `.github/workflows/`

Shipped as new `.github/workflows/publish-release.yml`, triggered by the
commit that adds a new `releases/manifests/manifest-<version>.json` to
`main` (diffing `github.event.before`/`after` for added manifest files)
rather than a git-tag push — this repo has never tagged dataset versions,
and inventing that convention just to satisfy a workflow trigger would
have been a bigger change than this item asked for. For each new version
it zips `releases/data/<version>/` (CSVs + `images/`) together with
`manifest.json` and `CHANGELOG.md` — matching `CLAUDE.md`'s "Release
package" contents exactly — writes a `sha256sum` checksum file, and
publishes both as a GitHub Release tagged `data-v<version>` via `gh
release create` (no third-party action needed; `gh` is preinstalled on
GitHub-hosted runners). Also exposed as `workflow_dispatch` with a
`version` input, to (re-)publish a specific version on demand — deletes
and recreates the release/tag first for idempotency on rerun. Verified
end-to-end against the real `releases/data/0.2.0/` (330 files, 11MB zip)
with a stubbed `gh`: the zip contents and computed checksum both came out
correct; a synthetic git-history test also confirmed the added-manifest
diff logic picks up exactly the new version(s) in a push, not
already-published ones.

### 34. Pokémon Profile empty state — RESOLVED, current behavior kept

- **Size**: S
- **Value**: The third open `docs/todo.md` M6 backlog item.
- **Blocked by**: nothing
- **Touches**: `pipelines/dashboard/static/app.js`

The existing item notes the current behavior — defaulting to the
highest-usage Pokémon — may actually be preferable to an empty state.
Decide before building.

Decided: keep defaulting to the highest-usage Pokémon, no code change.
Every other tab in this dashboard shows ranked content immediately on
open (Overview's Top 12, Usage's leaderboard, Team Builder's legal-pool
picker) per the "Ordering convention" — a blank Profile panel on first
load would be the one tab asking a visitor to act before showing them
anything. `.empty-state` is still used for the genuine empty case (a
stale selection resolving to no matching row). Documented in
`docs/design-system.md`'s new "Default selection, not an empty state
(Pokémon Profile)" subsection so this reads as a decision, not an
unaddressed gap.

---

## Section 3 — Platform, quality, and ops

Separated from the analytics list so it doesn't dilute it. These are
verified gaps, not speculative hardening. Items #36 and #38 were the two
with real correctness consequences; both are now done.

### 35. CI workflow — DONE

- **Size**: M
- **Value**: `make check` (lint + test + dbt build + validate) exists and
  nothing runs it automatically. There is no `.github/` directory at all.
- **Blocked by**: nothing
- **Touches**: new `.github/workflows/`

("No `.github/` directory at all" was already stale by the time this was
picked up — `scheduled-extraction.yml`/`deploy-dashboard.yml` exist — but
neither ran lint/test/dbt-build/validate on a push or PR, so the core gap
this item describes was real.) Shipped as new `.github/workflows/ci.yml`,
triggered on every PR and push to `main`. `lint`/`test` always run (pure
Python, no network dependency). `dbt-build`/`validate` need
`data/staging/*.csv`, which is gitignored and not committed — rather than
re-running extraction on every push (hitting OP.GG/PokéBase/MunchStats
repeatedly, which the extractors' own docstrings already flag an
unverified rate-limit/ToS posture for under `scheduled-extraction.yml`'s
daily cadence, let alone per-push), CI restores the same `actions/cache`
entry `scheduled-extraction.yml` populates (read-only, via
`actions/cache/restore`) and runs `dbt-build`/`validate` against that; on
a fresh fork with no scheduled run yet, that step degrades to a skipped
no-op rather than failing the job. This was caught firsthand: PR #40 (the
one that shipped backlog items #8/#10/#12/#13/#14) had zero CI checks run
against it before this item existed.

### 36. Fix vacuously-passing coverage tests — DONE

- **Size**: S
- **Value**: A correctness hole in the release gate. All four
  `assert_*_coverage.sql` tests return `10000` bps (100%) when the source
  has zero rows — so a total upstream outage that yields an empty CSV
  **passes every gate and can be released**.
- **Blocked by**: nothing
- **Touches**: `dbt/tests/singular/assert_*_coverage.sql`

Each test's zero-row branch now reports `0` bps instead of `10000`, so an
empty source fails the gate instead of passing it vacuously. Verified the
branch can only trigger for a genuinely empty (but present) snapshot file —
a missing one makes DuckDB's external-source glob raise an `IO Error`
before the query runs at all — so this doesn't newly break a fresh clone
with no extraction yet, only a real "extraction ran and returned nothing"
outage. Pairs with #40, which is still open.

### 37. Derive the validation report from dbt's manifest — DONE

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

The real gap was larger than the two named tests: `ability_detail`,
`item_detail`, and `move_detail`'s duplicate-key tests were invisible too
(five tests total, all added after the four dicts were last touched) —
exactly the "any new test is invisible until someone remembers to edit
report.py" failure mode this item describes, caught in the wild rather
than hypothetically. Fixed by removing the four dicts entirely: every
singular test SQL file now declares its own `{{ config(meta={category:
..., ...}) }}` (`dbt/tests/singular/*.sql`), and `report.py`'s
`build_report` iterates every test node in the manifest and buckets it by
`meta.category` instead of a name lookup. A test with no recognized
category lands in a new `uncategorized_checks` section (still eligible to
block a release on failure) rather than disappearing — closing the gap
for good, not just for these five tests. Verified against a real `dbt
build` + `extract all` pass: all 13 duplicate-key tables (the previously
-invisible four included) and all 9 referential-integrity checks now
appear in `validation_report.json` with real pass/fail status, and
`uncategorized_checks` is empty.

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

### 39. Source freshness gate — DONE

- **Size**: S
- **Value**: Nothing checks whether a snapshot is stale. The pipeline will
  happily validate and release six-month-old data with every gate green.
- **Blocked by**: nothing
- **Touches**: `dbt/models/staging/_sources.yml`,
  `pipelines/validate/report.py`

No `loaded_at_field` or `freshness:` block is configured anywhere, though
every row already carries `extracted_at_utc`.

Shipped: `_sources.yml`'s seven scheduled sources (PokéAPI + its three
detail feeds, OP.GG, MunchStats, PokéBase — Bulbagarden stays exempt,
it's deliberately on-demand-only) each gained a `freshness:` block
(`warn_after`/`error_after` mirroring `docs/dataset-spec.md`'s weekly/daily
cadences, doubled so one missed scheduled run warns rather than errors)
and a `loaded_at_field` casting `extracted_at_utc` to a timestamp (dbt's
freshness macro needs a real datetime, not the plain ISO-8601 string the
column actually is). `pipelines/cli.py`'s `_run_validate` now also runs
`dbt source freshness` (a separate command from `dbt build`) before
generating the report; `report.py`'s new `build_freshness_checks` reshapes
`target/sources.json` into a `freshness_checks` section, folding dbt's
"error" status into `release_blocking_findings` the same way any other
failing check is, while "warn" stays non-blocking. Verified against a real
`extract all` + `dbt source freshness` run: all seven sources report
`pass` with real `max_loaded_at`/age values in `validation_report.json`.

### 40. Row-count anomaly detection — DONE

- **Size**: M
- **Value**: Every current gate is a ratio or a duplicate count, so a source
  silently dropping from 106,000 rows to 500 passes all of them. Volume
  baselines catch the partial-outage case that #36 catches only in the total
  case.
- **Blocked by**: nothing, though #1's history makes baselines far easier
- **Touches**: `dbt/tests/singular/`, `pipelines/validate/report.py`

Shipped as a new dbt *generic* test — this project's first, per #42's own
observation that none existed — `dbt/macros/test_row_count_anomaly.sql`,
applied to each of the seven scheduled sources' `data_tests:` in
`_sources.yml` (same set freshness already covers; Bulbagarden stays
exempt for the same on-demand reason). It compares the latest
`snapshot_date`'s row count against the immediately preceding one (using
the append-only history #1/#2 already shipped) and fails below 50% of that
baseline; fewer than two snapshots (fresh clone, or a source extracted
only once) passes rather than failing vacuously, since there's no baseline
yet to call an anomaly against — a different case from #36's "present but
empty" fix, not a regression of it. Wired into
`pipelines/validate/report.py` as a new `row_count_anomaly_checks`
category (no hardcoded dict, following #37's meta.category pattern) and
`reports/validation/validation_report.template.json`. Verified against a
synthetic two-snapshot fixture (`dbt test -s
source_row_count_anomaly_staging_pokeapi_`): a 300→50 row drop fails at
1667bps, a 300→280 normal fluctuation passes, and a single-snapshot source
passes vacuously — plus a new `test_report.py` unit test for the
report-shaping side.

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

### 45. `pipelines/cli.py` test coverage — PARTIALLY DONE, stale "zero tests" claim

- **Size**: S
- **Value**: 74 unit tests cover the extractors, release, render, dashboard,
  and validation modules. The CLI — the only entry point to all of them —
  has **zero tests**. Argument parsing, subcommand dispatch, and both
  exit-code paths are entirely unexercised.
- **Blocked by**: nothing
- **Touches**: new `tests/unit/test_cli.py`

`tests/unit/test_cli.py` already exists (added alongside backlog #38's
fix) and isn't zero: 16 tests cover the snapshot-path helpers, `extract`
orchestration (including `all`), `dataset_version` defaulting/override, and
all four `validate` exit-code paths (clean pass, gate failure, unexpected
crash, stale `run_results.json`). Still genuinely uncovered: `main()`'s
argument-parsing/dispatch for the `release`, `render-card`, and
`build-dashboard` subcommands (e.g. `render-card`'s `--team-id`/`--spec`
mutual-exclusivity, `release`'s required `--version`) — narrower than this
entry originally described, but real.

Related, still true: there is no `conftest.py` or shared fixture module
anywhere under `tests/`, so each file re-declares its own helpers.

### 46. Dashboard JS duplication check — DONE, and it immediately caught a real bug

- **Size**: S
- **Value**: `pipelines/dashboard/static/app.js` and the committed
  `docs/dashboard/app.js` are byte-identical copies with nothing enforcing
  it. Editing the wrong one produces a published site that silently
  disagrees with its source.
- **Blocked by**: nothing
- **Touches**: `tests/`, or a `make` target

Shipped as `tests/unit/dashboard/test_static_duplication.py`, comparing
the three static scripts (`app.js`/`matchup.js`/`teams.js`) directly
against their committed `docs/dashboard/` copies (independent of
`build()`'s own copy step, so it also catches a hand-edit of the published
copy). This was not a hypothetical: the first run **failed for real** —
`pipelines/dashboard/static/app.js` had moved on through two more commits
(`00ef4d2`, `313acd2` — sub-tabs, icon-only type badges, a sortable moves
table) past the last time `docs/dashboard/app.js` was actually
republished, so the live GitHub Pages dashboard was missing real, already
-built UI features. Fixed by rerunning `make dashboard` and committing the
regenerated `docs/dashboard/`, which now passes the new test.

### 47. `sprites.py` rebuild ordering constraint — DONE

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

Took the first option: `copy_sprites` no longer `rmtree`s `images/` at
all. It now only unlinks the top-level `*.png` files it itself owns
(sprites live flat as `images/<pokemon_key>.png`), leaving sibling
subdirectories (`images/icons/`, `images/reference_teams/`, populated by
other `build.py` steps) untouched regardless of call order — the ordering
constraint is now moot rather than merely documented. New regression test
(`test_copy_sprites_does_not_clobber_sibling_asset_subdirectories`)
pre-populates an icons subdirectory before calling `copy_sprites` and
asserts it survives; the existing stale-sprite-cleanup test
(`test_copy_sprites_clears_stale_files_across_rebuilds`) still passes
unchanged.

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

### 49. Bps-based validation-report metrics read as 0 on a passing check

- **Size**: S
- **Value**: A real, previously-undetected correctness gap in the
  validation report and every release manifest's `quality_checks` block —
  discovered in this pass while verifying #29/#30 against a real
  `extract all` + `dbt build` + `validate` run, not a hypothetical.
- **Blocked by**: nothing
- **Touches**: `pipelines/validate/report.py` (`_ratio_from_bps`),
  `dbt/tests/singular/*.sql`'s `fail_calc`-based tests

Every coverage/null-rate/row-count-anomaly check reports its ratio via a
`fail_calc` override in basis points (the `assert_opgg_legal_pool_coverage.
sql`-style pattern documented in `report.py`'s own module docstring).
`_ratio_from_bps` assumes dbt's `run_results.json` always carries that
computed value in `failures`, regardless of pass/fail — true when a check
fails, **false when it passes**: dbt-core's `TestRunner.build_test_run_
result` (`dbt/task/test.py`) hardcodes `failures = 0` on the `TestStatus.
Pass` branch and only assigns `result.failures` (the real fail_calc value)
on the `Fail`/`Warn` branches. Confirmed directly against a real run: every
passing coverage/null-rate/row-count-anomaly check in a real `validation_
report.json` shows `metric_value: 0.0` (e.g. `opgg_legal_pool_coverage`
status `pass` but metric `0.0`, not the real ~0.95+), even though the
gating decision itself (`status`) is unaffected and correctly computed
dbt-side — **no release has ever shipped on a false pass**, but every
published manifest's `quality_checks` numbers for these checks have been
wrong since the ratio pattern was introduced.

Not a one-line fix: dbt gives no way to recover the real fail_calc value
on the passing path through `run_results.json` alone (confirmed by reading
`build_test_run_result`'s source directly, not assumed). The real fix has
to re-derive the value independently of dbt's pass/fail bookkeeping —
e.g. re-executing each bps test's already-compiled SQL (`run_results.json`
results already carry `compiled_code` per test) directly against
`dbt/data/warehouse.duckdb` from `report.py`, since that query is
deterministic and re-running it recovers the true ratio regardless of
status. Left as an open, precisely-scoped item rather than attempted
in-place, since it needs a DuckDB read path `report.py` doesn't have today
and careful handling of `compiled_code`'s relative `external_location`
paths (resolved relative to dbt's own working directory) — a rushed fix
risked getting those subtly wrong.

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
