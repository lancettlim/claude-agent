# Dashboard

M6's first-party analytics dashboard: a static site built from
`data/marts/*.csv` and published via GitHub Pages.

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
                                   names, computes KPIs and empty-state flags
pipelines/dashboard/build.py      renders templates/index.html.jinja with
                                   the payload baked in as inline JSON, and
                                   copies static/app.js alongside it
pipelines/dashboard/templates/    the single-page HTML/CSS template
pipelines/dashboard/static/       app.js — vanilla JS reading the baked-in
                                   data to wire filters, tables, and charts
        ↓
docs/dashboard/index.html         generated output — committed to git
docs/dashboard/app.js
```

Data is baked into `index.html` as `window.DASHBOARD_DATA = {...}` (an
inline `<script>` block) rather than fetched from a separate JSON file at
runtime. This is deliberate: `fetch()` of a local file is blocked by CORS
when `index.html` is opened directly via `file://` (no local server), and
inlining sidesteps that entirely while working identically once served
over `https://` by GitHub Pages.

The dashboard degrades gracefully in two ways:
- If `data/marts/*.csv` files don't exist yet (before `make dbt-build` has
  run), each mart loads as an empty list rather than erroring — the page
  still builds, just with empty sections.
- If a network can't reach the Chart.js CDN (e.g. a restricted sandbox),
  `app.js` checks `typeof Chart` before drawing and simply skips chart
  rendering — tables and KPI cards still populate normally, and no console
  errors are thrown.

## Building and viewing locally

```
make dashboard                     # runs dbt-build, then builds the site
# or, if data/marts/*.csv is already current:
python -m pipelines.cli build-dashboard
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
output), **`docs/dashboard/index.html` and `docs/dashboard/app.js` are
committed to git.** There is no CI/Actions workflow that rebuilds the
dashboard — GitHub Pages serves exactly what's checked in, so after
running `make dashboard`, `git add`/commit the regenerated files for the
live site to update.

`docs/.nojekyll` is committed alongside them so GitHub Pages serves the
`/docs` folder as plain static files, without Jekyll trying to process the
generated HTML or the repo's other `docs/*.md` narrative files.

**Enabling GitHub Pages itself is a manual step that can't be done via
git**: in the repo's GitHub Settings → Pages, set the source to "Deploy
from a branch", branch `main` (or whichever branch is the default), folder
`/docs`. Once enabled, the dashboard is reachable at
`https://<owner>.github.io/<repo>/dashboard/`.

## Data-reality caveats

As of this writing:
- **Stat changes**: every `stat_total_delta` in `stat_change_leaderboard`
  is `0` — no Champions rebalance has happened yet in the current
  extraction snapshot. The dashboard's stat-change leaderboard section
  shows an honest empty-state message instead of a chart of all-zero bars.
- **Trend over time**: there is only one `snapshot_date` so far, so there's
  nothing to plot a trend against yet. The legal-pool-by-regulation trend
  section shows an empty-state message for the same reason.
- **Regulation filtering**: `regulation_code` values (`m-a`, `m-b`) are
  populated (via PokéBase), so the current KPI card and
  `legality_summary_by_regulation` data are real and non-degenerate — only
  the *time-series* trend view is blocked on having more than one snapshot.

`data.py`'s `compute_flags` (`stat_changes_degenerate`,
`trend_degenerate`) drives which sections show real data versus an
empty-state banner, so these sections will light up automatically — no
code changes needed — once more extractor runs accumulate additional
snapshots and a real rebalance occurs.
