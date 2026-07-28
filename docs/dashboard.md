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
pass replaced every chart with a dependency-free ranked-list component,
and the later competitive-UX redesign pass replaced *that* with a
dependency-free 6-wide grid (`docs/design-system.md`'s "6-wide grid"),
so there is no longer a charting-library dependency at all.

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
                                   type and item icons, copies
                                   pre-rendered Pro Team Gallery cards,
                                   renders templates/index.html.jinja with
                                   the payload baked in as inline JSON, and
                                   copies static/app.js + matchup.js +
                                   teams.js alongside it
pipelines/dashboard/templates/    the tabbed HTML/CSS template
pipelines/dashboard/static/       app.js (tab framework, .grid-6xn,
                                   Overview/Usage/Pokémon Profile/Speed
                                   Tiers, shared helpers exported on
                                   window.DashboardApp), matchup.js
                                   (Matchup tab), teams.js (Team Builder +
                                   Top Teams tabs) — see
                                   docs/design-system.md's tab-registration
                                   note for how the three files share state
pipelines/dashboard/static/icons/ 18 committed move-type icon PNGs, also
                                   reused for the Pokémon-type badge/
                                   Matchup tab's type-effectiveness grid
data/reference_teams/             curated Pro Team Gallery specs + pre-
                                   rendered card PNGs (committed, see
                                   "Pro Team Gallery" below)
        ↓
docs/dashboard/index.html         generated output — committed to git
docs/dashboard/app.js
docs/dashboard/matchup.js
docs/dashboard/teams.js
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
vanilla JS — no routing library, no page reload). The competitive-UX
redesign pass removed Archetypes and Regulations, added Matchup and Top
Teams, and restructured every remaining tab around
`docs/design-system.md`'s "3-tier tab layout convention"
(filters → `.grid-6xn` → optional detail table):

- **Overview** — the KPI cards plus a "Top 12" `.grid-6xn`, ranked by
  `usage_share`. (The old "Top 30" ranked list was removed — the Usage tab
  is the full leaderboard now.)
- **Usage** — tier/type/role/usage-%/speed filters, a `.grid-6xn` of
  usage-share leaders, a full Usage leaders table, then the same
  grid+table pattern again for Win rate leaders (with a minimum-recorded-
  matches filter).
- **Pokémon Profile** — a single Pokémon picker (sorted by usage
  relevance, not alphabetically) driving: a profile header (base stats,
  speed-tier badge, and now a type badge), then three separate `.grid-6xn`
  sections — **Items** (top 5), **Ability** (top 5), **Moves** (top 15) —
  each tile showing a PokéAPI `short_effect` description, replacing the
  old single combined item×ability build table. **Team Cores** (most-
  frequent partners) keeps its own `.grid-6xn` section below those.
- **Speed Tiers** — every currently-legal Pokémon's Champions-format base
  Speed stat, fastest first, with type/speed-range filters, a `.grid-6xn`,
  and a full sortable table bucketed into Blazing/Fast/Average/Slow badges
  (see `docs/design-system.md`'s "Speed-tier badge")
- **Matchup** *(new)* — pick an attacker and defender Pokémon: a type-
  effectiveness grid, a stats/setup/weather damage calculator with a
  curated item/ability toggle list, and a co-usage `.grid-6xn` (a
  teammate-pairing proxy, explicitly not a real matchup-outcome signal).
  See `docs/design-system.md`'s "Matchup" section for the full scope note
  and what mechanics are/aren't modeled.
- **Team Builder** — a fully client-side roster builder: search/sort/
  type-filter the legal pool, add up to 6 Pokémon, see each slot's stats/
  top ability/top-4-move picker, their speed order, usage/win-rate/speed
  averages, and an "Export as pokepaste text" button (see
  `docs/design-system.md`'s "Team Builder"); the team persists to
  `localStorage` only, never sent anywhere.
- **Top Teams** *(new)* — a pokepaste (Showdown-export-text) paste-in box
  that loads a team into Team Builder, a `.grid-6xn` leaderboard fed by the
  new `top_tournament_teams` mart (real MunchStats team data, ranked by
  win_rate), and the **Pro Team Gallery** (see below), moved here from
  Team Builder.

Usage leaders, Speed Tiers, Pokémon Profile, Matchup, and Team Builder's
picker all pull from `data/marts/pokemon_champions_profile.csv` — a mart
(one row per currently-legal Pokémon, joining `pokemon_stat_champions`
with `pokemon` for type, `pokemon_usage_summary`, and
`pokemon_win_rate_summary`) purpose-built so these views don't have to
join multiple marts client-side.

Each tab's setup function still runs lazily on that tab's first activation
(`App.registerTab(tabId, fn)` in `app.js`, called from all three JS files)
rather than eagerly on page load — see `docs/design-system.md`'s note on
how Team Builder and Top Teams coordinate shared team state despite that
laziness (`ensureTeamBuilder()`).

## Cumulative legal pool

`legality_summary_by_regulation.cumulative_legal_pokemon_count` (used by
the "Legal Pool" KPI card — the dedicated Regulations tab that also showed
this was removed in the competitive-UX redesign pass, see "Removed
sections" below) is a **naive union**: regulation B's cumulative count
includes every Pokémon legal in regulation A too, assuming regulation
codes sort lexicographically in release order. PokéBase (the sole source
of `legality_snapshot`) never publishes a removal signal — a Pokémon's
absence from a later regulation's snapshot isn't distinguishable from "not
yet observed" vs. "actually banned." This means the cumulative count can
only grow; if a Pokémon were genuinely banned in a later regulation, this
count would keep including it anyway. Treat it as an upper bound, not a
confirmed current pool.

## Archetype Explorer (removed)

The Archetype Explorer tab was removed in the competitive-UX redesign
pass (see "Removed sections" below) — this section is kept for history.
`pokemon_archetype_usage`/`archetype_summary` (still dbt-built, just no
longer loaded by the dashboard) were built from `dbt/seeds/
archetype_pokemon_map.csv` — a **curated, editorial** seed (named
competitive strategies like "Rain," "Trick Room," "Sun" mapped to their
member Pokémon), not derived from any extractor. This was an explicit
exception to this repo's "provenance is mandatory" convention, made
because no in-scope source publishes team-composition/archetype labels at
all — see `dbt/seeds/schema.yml`'s entry for the seed's editable format if
a future pass wants to reintroduce archetype context elsewhere (e.g. as a
Team Builder tag).

## Pro Team Gallery

A grid of real tournament teams, rendered as broadcast-style cards via
`pipelines/render/` (the same tool `render-card` uses standalone) and
shown for reference/inspiration in the **Top Teams** tab (moved here from
Team Builder in the competitive-UX redesign pass, alongside the real
`top_tournament_teams` leaderboard and the pokepaste importer — see
"Tabs" above) — distinct from, and not part of, Team Builder's own
roster-planner feature.

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
- **Item icons** (open-ended, data-dependent): resolved for every distinct
  `item_name` in `pokemon_item_usage`, preferring `pipelines/render/
  bulbagarden_items.py`'s `ensure_item_icon_bulbagarden()` (Bulbagarden
  Archives held-item sprites, "File:Bag &lt;Item Name&gt; Sprite.png" and a
  couple of naming-variant fallbacks) and falling back per-item to
  `pipelines/render/assets.py`'s `ensure_item_icon()` (PokéAPI community
  sprites) on a Bulbagarden resolution miss, so an item that used to
  resolve via PokéAPI never regresses to no icon. This is the one part of
  a dashboard build that needs network access. Pass `--no-fetch-icons` to
  `build-dashboard` (or `fetch_icons=False` to
  `pipelines.dashboard.build.build`) for an offline build — item names
  render text-only in that case.
- **Pokémon type icons**: the Pokémon Profile type badge and the Matchup
  tab's type-effectiveness grid reuse the same 18 committed move-type
  icons above (types and move-types share one 18-value namespace) — no
  new icon assets were needed to add Pokémon type display.

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
`docs/dashboard/images/` are committed to git.** There is still no CI/
Actions workflow that *rebuilds* the dashboard (that would require live
network access to all five extractors' upstream sources, which isn't
something CI should do unsupervised) — after running `make dashboard`,
`git add`/commit the regenerated files (including `images/`) as before.

What *is* automated (`.github/workflows/deploy-dashboard.yml`) is
*publishing* what's committed: a push to `main` touching anything under
`docs/` triggers a GitHub Actions job that uploads the `docs/` folder as a
Pages artifact and deploys it via `actions/deploy-pages`, rather than
relying on GitHub Pages' own branch-polling deployment (which is what
caused stale/inconsistently-refreshed live-site content before this
workflow existed). It can also be run manually via the Actions tab
(`workflow_dispatch`).

`docs/.nojekyll` is committed alongside the dashboard files so the
published site serves plain static files, without Jekyll trying to process
the generated HTML or the repo's other `docs/*.md` narrative files.

**Pointing GitHub Pages at Actions-based deployment is a manual step that
can't be done via git**: in the repo's GitHub Settings → Pages, set the
source to "GitHub Actions" (not "Deploy from a branch" — that's the older
mode this workflow replaces). Once set, every push to `main` that touches
`docs/` redeploys via the workflow above, and the dashboard is reachable at
`https://<owner>.github.io/<repo>/dashboard/` — for this repo, that's
https://lancettlim.github.io/claude-agent/dashboard/.

`docs/index.html` is a static redirect stub (meta-refresh + JS
`location.replace`, so it works with JS disabled too) that sends
`https://<owner>.github.io/<repo>/` itself to `dashboard/` — the site root
would otherwise 404, since nothing else lives at `docs/`'s top level.

## Data-reality caveats

As of this writing:
- **Regulation filtering**: `regulation_code` values (`m-a`, `m-b`) are
  populated (via PokéBase), so the "Legal Pool" KPI card's
  `legality_summary_by_regulation` data is real and non-degenerate, even
  though there's no longer a dedicated tab surfacing per-regulation detail.
- **Cumulative legal pool**: see "Cumulative legal pool" above — can only
  grow, never confirmed to reflect a real later-regulation ban.
- **Archetype Explorer**: removed — see "Archetype Explorer (removed)"
  above. Was always curated editorial data, not sourced tournament data.
- **Matchup tab**: type effectiveness and the damage calculator's type/
  move-power inputs are real PokéAPI data; the co-usage panel is an
  explicitly-labeled teammate-pairing proxy, not real battle-outcome data
  (see `docs/design-system.md`'s "Matchup tab scope").
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

The (also since-removed) **Regulations** tab was a different thing from
the removed legal-pool-trend section, worth distinguishing historically:
legal-pool trend would have compared the *same* regulation across
multiple `snapshot_date`s (still degenerate — only one snapshot exists),
while Regulation Comparison compared *different regulations* within one
snapshot (real, non-degenerate data, since `m-a`/`m-b` are both populated
today) — it just wasn't kept, unlike the permanently-empty sections above.

## Removed tabs (competitive-UX redesign pass)

Unlike the stat-change-leaderboard/legal-pool-trend removal above (cut
because the underlying data was permanently degenerate), the **Archetypes**
and **Regulations** tabs were removed by explicit request even though
their data was real and non-degenerate — a scope/UX decision, not a
data-availability one. `legality_summary_by_regulation` still loads (it
feeds the "Legal Pool" KPI card); `pokemon_archetype_usage`/
`archetype_summary` and the `archetype_pokemon_map` seed are untouched at
the data/dbt layer, just no longer read by `pipelines/dashboard/data.py`.
See `docs/design-system.md`'s "Removed tabs and components" for the full
rationale, and `docs/todo.md`'s M6 backlog for the redesign pass this was
part of.
