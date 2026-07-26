# Dashboard

M6's first-party analytics dashboard: a static site built from
`data/marts/*.csv` and published via GitHub Pages. This document covers
architecture and build/publish mechanics; see `docs/design-system.md` for
the dashboard's design tokens, component catalog, and Pokémon-
representation/naming/ordering conventions.

## Stack decision

`docs/prd.md`'s open question ("Which dashboard tool stack and hosting
model should be used for Phase 1?") is resolved as: a static
HTML/CSS/vanilla-JS page — Jinja2-rendered, no charting library, no
backend, no build tooling (no npm, no bundler). An earlier version of this
page used Chart.js (CDN-loaded) for its bar charts; the broadcast-redesign
pass replaced every chart with a dependency-free ranked-list component
(`docs/design-system.md`'s "Ranked list"), so there is no longer a
charting-library dependency at all.

This was chosen because GitHub Pages only serves static files (no server),
which rules out a Python server-based dashboard (Streamlit, Dash, Flask)
for a zero-hosting-cost deployment, and because it's the lightest-weight
option that satisfies the PRD's KPI/trend/drill-down requirements. See
`docs/todo.md`'s M6 backlog item for a possible future dynamic
Python/Streamlit dashboard once the dataset has enough snapshots/trend data
to justify the added hosting complexity.

## Architecture

```
pipelines/dashboard/data.py       reads data/marts/*.csv, joins pokemon
                                   names, computes KPIs
pipelines/dashboard/sprites.py    copies Bulbagarden species sprites
                                   (keyed by pokemon_key) into output/images/
pipelines/dashboard/build.py      calls data.py + sprites.py, resolves
                                   move-type and item icons, copies
                                   pre-rendered Pro Team Gallery cards,
                                   renders templates/index.html.jinja with
                                   the payload baked in as inline JSON, and
                                   copies static/app.js alongside it
pipelines/dashboard/templates/    the tabbed HTML/CSS template
pipelines/dashboard/static/       app.js — vanilla JS reading the baked-in
                                   data to wire tabs, filters, tables, and
                                   ranked lists
pipelines/dashboard/static/icons/ 18 committed move-type icon PNGs
data/reference_teams/             curated Pro Team Gallery specs + pre-
                                   rendered card PNGs (committed, see
                                   "Pro Team Gallery" below)
        ↓
docs/dashboard/index.html         generated output — committed to git
docs/dashboard/app.js
docs/dashboard/images/            sprites + type/item icons + gallery
                                   cards — committed to git
```

Data is baked into `index.html` as `window.DASHBOARD_DATA = {...}` (an
inline `<script>` block) rather than fetched from a separate JSON file at
runtime. This is deliberate: `fetch()` of a local file is blocked by CORS
when `index.html` is opened directly via `file://` (no local server), and
inlining sidesteps that entirely while working identically once served
over `https://` by GitHub Pages.

Pokémon sprites, move-type icons, and item icons are copied/resolved into
`docs/dashboard/images/` as separate committed files rather than inlined as
base64 — the payload JSON is already large (hundreds of usage/build/move/
team-core rows), and base64 would add ~33% overhead across ~250 sprites,
bloating the one committed HTML file and making its diffs unreadable.
Separate PNGs keep diffs scoped to changed images and are browser-cacheable
across page loads, mirroring the `releases/data/<version>/images/` pattern
used by release packages.

The dashboard degrades gracefully in several ways:
- If `data/marts/*.csv` files don't exist yet (before `make dbt-build` has
  run), each mart loads as an empty list rather than erroring — the page
  still builds, just with empty sections.
- If a Pokémon referenced by a mart has no Bulbagarden sprite yet (or
  `data/assets/bulbagarden/` isn't populated at all), `sprites.py` skips it
  with a warning rather than raising — the dashboard falls back to
  text-only Pokémon names wherever a sprite is missing.
- Item icons (see "Icon sources" below) are resolved best-effort over the
  network; an unresolved or unreachable item icon degrades to a text-only
  item name, never a build failure.
- If `data/reference_teams/` doesn't exist yet, the Pro Team Gallery
  renders an empty-state message rather than erroring (see "Pro Team
  Gallery" below).

## Tabs

The page is a single scrolling KPI row plus seven tabs (client-side,
vanilla JS — no routing library, no page reload):

- **Overview** — the KPI cards, a "Top 12" spotlight card grid, and a
  "Top 30" ranked list (first 10 shown, "Show all 30" to expand), all
  ranked by `usage_share`
- **Usage** — a per-tournament-tier ranked list, a Usage leaders table
  (rank, Pokémon, `usage_share` as % of meta — sortable columns), and a
  Win rate leaders table (with a minimum-recorded-matches filter)
- **Pokémon Profile** — a single Pokémon picker (sorted by usage
  relevance, not alphabetically) driving three sub-sections: Profile
  (base stats, speed-tier badge, curated archetype tags), Build & Moveset
  (item/ability table + move ranked list, both by their `_share` of this
  Pokémon's own recorded builds/moves), and Team Cores (ranked list of
  most-frequent partners). Replaces the earlier separate Builds/Moves/
  Team Cores tabs, which had three independent, unsynced Pokémon pickers.
- **Archetypes** — the Archetype Explorer: a card grid of curated
  competitive archetypes (`docs/design-system.md`'s "Archetype card"),
  each with a disclaimer that membership is editorial curation, not
  sourced tournament data; selecting a card filters a member table below.
- **Regulations** — the Regulation Comparison: cumulative legal-pool size
  per regulation (see "Cumulative legal pool" below) plus a delta vs. the
  previous regulation.
- **Speed Tiers** — every currently-legal Pokémon's Champions-format base
  Speed stat, fastest first, with a ranked list (top 20) and a full table
  bucketed into Blazing/Fast/Average/Slow badges (see
  `docs/design-system.md`'s "Speed-tier badge")
- **Team Builder** — a fully client-side roster builder: search/sort the
  legal pool, add up to 6 Pokémon, see their speed order and
  usage/win-rate/speed averages (see `docs/design-system.md`'s "Team
  Builder"); the team persists to `localStorage` only, never sent
  anywhere. Below it, the **Pro Team Gallery** (see below) — a separate,
  read-only reference feature.

Usage leaders, Speed Tiers, Pokémon Profile, and Team Builder's picker all
pull from `data/marts/pokemon_champions_profile.csv` — a mart (one row per
currently-legal Pokémon, joining `pokemon_stat_champions` with
`pokemon_usage_summary` and `pokemon_win_rate_summary`) purpose-built so
these views don't have to join multiple marts client-side.

Each tab's setup function runs lazily on that tab's first activation
rather than eagerly on page load (see `app.js`'s `tabInitializers`) — this
predates and is unrelated to the earlier Chart.js-canvas-sizing rationale,
since there's no canvas involved anymore.

## Cumulative legal pool

`legality_summary_by_regulation.cumulative_legal_pokemon_count` (used by
the Regulations tab and the "Legal Pool" KPI card) is a **naive union**:
regulation B's cumulative count includes every Pokémon legal in regulation
A too, assuming regulation codes sort lexicographically in release order.
**Caveat, shown as visible UI copy on the Regulations tab, not just a code
comment**: PokéBase (the sole source of `legality_snapshot`) never
publishes a removal signal — a Pokémon's absence from a later regulation's
snapshot isn't distinguishable from "not yet observed" vs. "actually
banned." This means the cumulative count can only grow; if a Pokémon were
genuinely banned in a later regulation, this count would keep including it
anyway. Treat it as an upper bound, not a confirmed current pool.

## Archetype Explorer

`pokemon_archetype_usage`/`archetype_summary` are built from
`dbt/seeds/archetype_pokemon_map.csv` — a **curated, editorial** seed
(named competitive strategies like "Rain," "Trick Room," "Sun" mapped to
their member Pokémon), not derived from any extractor. This is an explicit
exception to this repo's "provenance is mandatory" convention, made
because no in-scope source publishes team-composition/archetype labels at
all. The dashboard always presents this with disclaimer copy making the
distinction clear, and the seed needs manual upkeep as the real metagame
shifts — see `dbt/seeds/schema.yml`'s entry for the seed's editable format.

## Pro Team Gallery

A grid of real tournament teams, rendered as broadcast-style cards via
`pipelines/render/` (the same tool `render-card` uses standalone) and
shown for reference/inspiration inside the Team Builder tab — distinct
from, and not part of, the roster-planner feature above it.

Cards are **pre-rendered ahead of time**, not generated at dashboard-build
time or in the browser: there's no Playwright dependency in
`build-dashboard` itself, keeping it fast and network-optional (same
`--no-fetch-icons` offline story as item icons). The workflow to add a
gallery entry:

1. Write a build spec at `data/reference_teams/specs/<name>.json` (the
   same ad-hoc JSON format `render-card --spec` accepts — see
   `pipelines/render/data_source.py`'s `load_from_spec` docstring — with
   optional top-level `player_name`/`country`).
2. Render it: `python -m pipelines.cli render-card --spec
   data/reference_teams/specs/<name>.json --output
   data/reference_teams/cards/<name>.png`.
3. Add an entry to `data/reference_teams/reference_teams.json`: `{team_id,
   player_name, country, event_name, placement, archetype_key,
   pokemon_keys, card_image}` — `pokemon_keys` (the 6 `pokemon_key` slugs)
   drives the gallery card's "Load into my builder" button;
   `card_image` is the filename from step 2, relative to
   `data/reference_teams/cards/`.
4. Commit the spec, the PNG, and the updated `reference_teams.json` — like
   `docs/dashboard/`, this is generated-but-committed content
   (`pipelines/dashboard/build.py`'s `_load_reference_teams` just copies
   the already-rendered PNGs into the published site).

**Known gaps, not code bugs**: MunchStats's real tournament data doesn't
report Nature at all for most entries (~17% coverage as of this writing;
see `pipelines/extract/munchstats.py`'s docstring) — `nature` on a
gallery card built from a hand-authored spec (rather than a real
`team_id`) is only as complete as what you write into the spec. Country
codes are two-letter (e.g. "US", "GB") per MunchStats's own format,
rendered as plain text — no flag-emoji/ISO-lookup table exists yet.

## Icon sources

Three distinct assets, three distinct strategies:

- **Species sprites** (~250 Pokémon): copied from the gitignored
  `data/assets/bulbagarden/` cache (populated by
  `python -m pipelines.cli extract bulbagarden`) via `pipelines/dashboard/
  sprites.py`, keyed by `pokemon_key` so `app.js` can look them up the same
  way it looks up every other Pokémon-keyed field. Purely a local file
  copy — no network access at dashboard-build time.
- **Move-type icons** (18, fixed): bundled as committed static assets under
  `pipelines/dashboard/static/icons/types/`, bootstrapped once via
  `pipelines/render/assets.py`'s `ensure_type_icon()` and copied verbatim
  into `docs/dashboard/images/icons/types/` on every build. No network
  dependency — types never change.
- **Item icons** (open-ended, data-dependent): resolved via
  `pipelines/render/assets.py`'s `ensure_item_icon()` (PokéAPI community
  sprites) for every distinct `item_name` in `pokemon_build_usage`. This is
  the one part of a dashboard build that needs network access. Pass
  `--no-fetch-icons` to `build-dashboard` (or `fetch_icons=False` to
  `pipelines.dashboard.build.build`) for an offline build — item names
  render text-only in that case.

## Team-core drill-down

`dbt/models/marts/pokemon_team_core_usage.sql` closes a gap named in
`docs/prd.md`'s original scope ("Drill-down by Pokémon, team core, move,
and item usage") but never built until this pass: it self-joins
`tournament_team_member` on `team_id` to count how often each pair of
Pokémon appears on the same tournament team, restricted to the current
legal pool, mirrored into both anchor directions so either Pokémon in a
pair can be the drill-down's selected anchor.

## Building and viewing locally

```
make dashboard                     # runs dbt-build, then builds the site
# or, if data/marts/*.csv is already current:
python -m pipelines.cli build-dashboard
# offline (skips fetching item icons over the network):
python -m pipelines.cli build-dashboard --no-fetch-icons
```

View it either by opening the file directly:

```
open docs/dashboard/index.html     # works via file://, no server needed
```

or by serving it the way GitHub Pages will:

```
python -m http.server --directory docs/dashboard
```

## Publishing (GitHub Pages)

Unlike other pipeline output in this repo (`data/normalized/`,
`data/marts/`, `data/staging/` are all gitignored regenerated build
output), **`docs/dashboard/index.html`, `docs/dashboard/app.js`, and
`docs/dashboard/images/` are committed to git.** There is no CI/Actions
workflow that rebuilds the dashboard — GitHub Pages serves exactly what's
checked in, so after running `make dashboard`, `git add`/commit the
regenerated files (including `images/`) for the live site to update.

`docs/.nojekyll` is committed alongside them so GitHub Pages serves the
`/docs` folder as plain static files, without Jekyll trying to process the
generated HTML or the repo's other `docs/*.md` narrative files.

**Enabling GitHub Pages itself is a manual step that can't be done via
git**: in the repo's GitHub Settings → Pages, set the source to "Deploy
from a branch", branch `main` (or whichever branch is the default), folder
`/docs`. Once enabled, the dashboard is reachable at
`https://<owner>.github.io/<repo>/dashboard/` — for this repo, that's
https://lancettlim.github.io/claude-agent/dashboard/.

`docs/index.html` is a static redirect stub (meta-refresh + JS
`location.replace`, so it works with JS disabled too) that sends
`https://<owner>.github.io/<repo>/` itself to `dashboard/` — the site root
would otherwise 404, since nothing else lives at `docs/`'s top level.

## Data-reality caveats

As of this writing:
- **Regulation filtering**: `regulation_code` values (`m-a`, `m-b`) are
  populated (via PokéBase), so the current KPI card's and Regulations
  tab's `legality_summary_by_regulation` data is real and non-degenerate.
- **Cumulative legal pool**: see "Cumulative legal pool" above — can only
  grow, never confirmed to reflect a real later-regulation ban.
- **Archetype Explorer**: see "Archetype Explorer" above — curated
  editorial data, not sourced tournament data.
- **Date-range/trend views**: still not buildable — only one
  `snapshot_date` exists in the data so far (see "Removed sections"
  below).

## Removed sections (as of this pass)

The stat-change leaderboard and legal-pool-trend-by-regulation sections
were removed from the page (see `docs/todo.md`'s dashboard refinement
plan): both were structurally built but permanently showed an
empty-state banner, since today's dataset has zero nonzero stat deltas
(no Champions rebalance has occurred yet) and only one `snapshot_date`
(nothing to trend against). Rather than ship two sections that always
render as "not enough data yet," they were cut until the underlying data
exists. `pipelines/dashboard/data.py` no longer loads
`stat_change_leaderboard` or computes degenerate-data flags; re-adding
these views once a rebalance happens and multiple snapshots accumulate is
a small, self-contained addition (reintroduce the mart load, the two
template sections, and their `app.js` render functions — see git history
for the removed code).

By contrast, the "Tabs", "Icon sources", and "Team-core drill-down"
sections above are additive against this same original scope: they cover
a PRD-named drill-down (team core) and refinement-pass backlog items
(mobile layout, richer imagery) that had real, non-degenerate data
available, unlike the two removed sections.

The new **Regulations** tab is a different thing from the removed
legal-pool-trend section, worth distinguishing: legal-pool trend would
compare the *same* regulation across multiple `snapshot_date`s (still
degenerate — only one snapshot exists), while Regulation Comparison
compares *different regulations* within one snapshot (real, non-degenerate
data, since `m-a`/`m-b` are both populated today).
