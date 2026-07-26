# Dashboard

M6's first-party analytics dashboard: a static site built from
`data/marts/*.csv` and published via GitHub Pages. This document covers
architecture and build/publish mechanics; see `docs/design-system.md` for
the dashboard's design tokens, component catalog, and Pokémon-
representation/naming/ordering conventions.

## Stack decision

`docs/prd.md`'s open question ("Which dashboard tool stack and hosting
model should be used for Phase 1?") is resolved as: a static
HTML/CSS/vanilla-JS page — Jinja2-rendered, [Chart.js](https://www.chartjs.org/)
loaded from a CDN, no backend, no build tooling (no npm, no bundler).

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
                                   move-type and item icons, renders
                                   templates/index.html.jinja with the
                                   payload baked in as inline JSON, and
                                   copies static/app.js alongside it
pipelines/dashboard/templates/    the tabbed HTML/CSS template
pipelines/dashboard/static/       app.js — vanilla JS reading the baked-in
                                   data to wire tabs, filters, tables, and
                                   charts
pipelines/dashboard/static/icons/ 18 committed move-type icon PNGs
        ↓
docs/dashboard/index.html         generated output — committed to git
docs/dashboard/app.js
docs/dashboard/images/            sprites + type/item icons — committed to git
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
- If a network can't reach the Chart.js CDN (e.g. a restricted sandbox),
  `app.js` checks `typeof Chart` before drawing and simply skips chart
  rendering — tables and KPI cards still populate normally, and no console
  errors are thrown.
- If a Pokémon referenced by a mart has no Bulbagarden sprite yet (or
  `data/assets/bulbagarden/` isn't populated at all), `sprites.py` skips it
  with a warning rather than raising — the dashboard falls back to
  text-only Pokémon names wherever a sprite is missing.
- Item icons (see "Icon sources" below) are resolved best-effort over the
  network; an unresolved or unreachable item icon degrades to a text-only
  item name, never a build failure.

## Tabs

The page is a single scrolling KPI row plus seven tabs (client-side,
vanilla JS — no routing library, no page reload):

- **Overview** — the four KPI cards
- **Usage** — usage-by-tournament-tier chart, a Usage leaders table (rank,
  usage count, and `usage_share` as a percentage of the meta), and a
  Win rate leaders table
- **Builds** — item & ability drill-down, with item icons per row
- **Moves** — move drill-down chart, with move-type icons per row
- **Team Cores** — which Pokémon most often share a team with the selected
  Pokémon (see "Team-core drill-down" below)
- **Speed Tiers** — every currently-legal Pokémon's Champions-format base
  Speed stat, fastest first, with a bar chart (top 20) and a full table
  bucketed into Blazing/Fast/Average/Slow badges (see
  `docs/design-system.md`'s "Speed-tier badge")
- **Team Builder** — a fully client-side roster builder: search/sort the
  legal pool, add up to 6 Pokémon, see their speed order and
  usage/win-rate/speed averages (see `docs/design-system.md`'s "Team
  Builder"); the team persists to `localStorage` only, never sent
  anywhere

Usage leaders, Speed Tiers, and Team Builder's picker all pull from
`data/marts/pokemon_champions_profile.csv` — a new mart (one row per
currently-legal Pokémon, joining `pokemon_stat_champions` with
`pokemon_usage_summary` and `pokemon_win_rate_summary`) purpose-built so
these views don't have to join multiple marts client-side.

Chart.js canvases inside a hidden tab panel initialize at zero size, so
each tab's chart-drawing setup runs lazily on that tab's first activation
rather than eagerly on page load (see `app.js`'s `tabInitializers`).

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

## Data-reality caveats

As of this writing:
- **Regulation filtering**: `regulation_code` values (`m-a`, `m-b`) are
  populated (via PokéBase), so the current KPI card's
  `legality_summary_by_regulation` data is real and non-degenerate.

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
