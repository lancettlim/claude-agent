# Dashboard UX Design System

This is the design system for `pipelines/dashboard/` — the static
analytics dashboard described in `docs/dashboard.md`. It documents the
design tokens, component patterns, and Pokémon-representation/data
conventions the dashboard's HTML/CSS/JS (`templates/index.html.jinja`,
`static/app.js`) implement, so future additions stay visually and
behaviorally consistent instead of drifting per-tab. Where docs/dashboard.md
covers *architecture* (how the site is built and published), this document
covers *design*: what things look like, how Pokémon data is named and
ordered, and what a new component should reuse rather than reinvent.

This is a living document — when a new component or convention is added to
the dashboard, update this file in the same change.

## Design tokens

All tokens live as CSS custom properties on `:root` in
`templates/index.html.jinja`. Nothing in the stylesheet should hardcode a
color, spacing, or radius value that already has a token — add one instead.

### Color

| Token | Value | Use |
|---|---|---|
| `--navy` | `#16264d` | Primary text, borders |
| `--blue` | `#2b5cad` | Interactive accents (active tab, links, bars) |
| `--light-blue` | `#eaf1fb` | Subtle fills (empty states, table dividers, badge backgrounds) |
| `--muted` | `#5b6b8c` | Secondary text (labels, sub-text) |
| `--bg` | `#f4f6fb` | Page background |
| `--surface` | `#fff` | Card/section background |
| `--positive` / `--positive-bg` | `#1f8a4c` / `#e8f7ee` | Reserved for future positive-delta indicators (e.g. a stat gainer, once `stat_change_leaderboard` has real deltas — see "Removed sections" in `docs/dashboard.md`) |
| `--warning` / `--warning-bg` | `#a8710a` / `#fbf1e0` | Reserved for caution states |
| `--danger` / `--danger-bg` | `#b23434` / `#fbe9e9` | Destructive actions (Team Builder's remove button), Blazing speed tier |

Speed-tier colors (`--speed-blazing`, `--speed-fast`, `--speed-average`,
`--speed-slow`, each with a `-bg` pair) are documented under "Speed-tier
badge" below rather than here, since they're paired directly with the
bucketing thresholds.

### Spacing

A 4px base scale: `--space-1` (4px) through `--space-8` (32px). Prefer the
token nearest the ad-hoc pixel value you'd otherwise write.

### Radius

`--radius-sm` (6px, buttons/inputs/table containers), `--radius-md` (10px,
cards/sections/team slots), `--radius-pill` (999px, badges).

### Type scale

`--font-xs` (0.8rem, badges/sub-text) through `--font-2xl` (1.6rem, page
title). Body copy defaults to the browser's system font stack
(`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`) — no
webfont, keeping the page dependency-free.

## Layout primitives

- **`header`** — page title + generation timestamp, centered, white on the
  page background.
- **`main`** — centered content column, `max-width: 1100px`.
- **`.kpi-row`** — responsive grid of `.kpi-card`s (`auto-fit,
  minmax(200px, 1fr)`), always the first thing under the header.
- **`.tabs` / `.tab-btn` / `.tab-panel`** — client-side tab navigation
  (`app.js`'s `setupTabs`). Every dashboard view beyond the KPI row lives in
  a tab, not a scrolling section — this was a deliberate M6 redesign
  decision (see `docs/todo.md`'s "Dashboard full redesign" entry) to keep
  the page scannable as views are added.
- **`section` (`.tab-panel`)** — a bordered white card per tab, `h2` title,
  optional `.controls` filter row, then chart and/or table content.

## Component catalog

### KPI card

`.kpi-card`: a bordered white card with an optional 40px sprite, a
`.label` (uppercase, muted, small), a `.value` (bold, large), and an
optional `.sub` (muted, small) for supporting detail like a percentage or
date. Used only in the top `.kpi-row` — don't reuse this class for
in-tab summary stats; use `.stat-summary-row .stat` instead (see Team
Builder below), which is denser and doesn't compete visually with the
page-level KPIs.

### Leaderboard table

The recurring pattern for "top N Pokémon by some metric" (Usage leaders,
Win rate leaders, Speed tiers): a `<table>` inside `.table-scroll`, first
column a `.badge.badge-rank` (`#1`, `#2`, …), second column a
`pokemonCell()`-rendered sprite+name, remaining columns the metric(s). All
three of these tables are sorted server-computed-rank-then-client-rendered
in *descending* order of their primary metric by default — see "Ordering
convention" below.

### Badge

`.badge`: a small pill (`--radius-pill`, `--font-xs`, bold). Two variants
today:
- `.badge-rank` — neutral blue-on-light-blue, used for leaderboard rank.
- `.badge-speed-*` — see "Speed-tier badge" below.

Add new badge variants as `.badge-<name>` with a token-backed color pair,
not one-off inline styles.

### Sprite / icon cell

`pokemonCell(pokemonKey, pokemonName)` (in `app.js`) is the canonical way
to render a Pokémon in a table cell: a 24px sprite (from the `sprites` map,
keyed by `pokemon_key`) next to the display name, wrapped in
`.cell-with-icon`. `itemCell()` follows the same pattern for held items.
**Any new table or list that references a specific Pokémon should use
`pokemonCell()` (or `spriteImg()` directly for non-table contexts, as
Team Builder's roster list and team slots do) rather than rendering a bare
name** — see "Representing Pokémon" below.

### Chart (bar, with sprite axis + external tooltip)

`drawBarChart()` is the single shared Chart.js wrapper (Usage, Moves,
Team Cores, and Speed Tiers charts all call it). It handles: collapsing
gracefully when Chart.js's CDN didn't load, an optional `spriteAxisPlugin`
that draws a 22px Pokémon sprite under each x-axis tick instead of a text
label, and an optional DOM-based external tooltip (`.chart-tooltip`) that
can embed a sprite/icon image next to the value — Chart.js's canvas
tooltips can't embed `<img>` elements natively. New charts referencing
Pokémon should pass `spriteSources`/`tooltipInfoFn` rather than drawing a
bespoke chart.

### Filter control

`.controls label` — a small-caps muted label wrapping a `<select>` or
`input[type=text]`. Selects default to `font-size: 16px` specifically to
prevent iOS Safari's auto-zoom-on-focus; keep that when adding new inputs
(see Team Builder's search box).

### Empty state

`.empty-state` — light-blue rounded box, muted text. Used for the
Overview tab's explanatory copy today; also the pattern to reach for if a
future view needs a "not enough data yet" message (see `docs/dashboard.md`'s
"Removed sections" — this is what the stat-change leaderboard and
legal-pool-trend sections would use if/when they're reintroduced).

### Buttons

`.btn` — bordered, `--radius-sm`, hover fills `--light-blue`. `.btn-primary`
is the solid-blue variant (not currently used, reserved for a future
primary action). `.btn-remove` is a borderless text-only danger-colored
button (Team Builder's per-slot remove). `.btn-sm` is a compact size
modifier (Team Builder's "Add"/"Clear team" buttons).

### Speed-tier badge

Buckets a Pokémon's Champions-format base Speed stat
(`pokemon_champions_profile.speed`) into four bands, each rendered as a
`.badge-speed-*` pill. Thresholds live in `app.js`'s `SPEED_TIERS`
constant — **this table must stay in sync with that constant**:

| Tier | Speed range | Badge color |
|---|---|---|
| Blazing | ≥ 120 | danger red |
| Fast | 90–119 | warning amber |
| Average | 60–89 | blue |
| Slow | ≤ 59 | muted gray |

These bands are a display/UX bucketing of real Champions-format speed
data, not a separate data source — no new extraction or fabricated values
are involved. They're intentionally coarse (four bands) rather than
per-point tiers, since Champions' actual competitive speed-tier list
changes as the legal pool and rebalances change; the dashboard's job is to
make the real numbers scannable, not to assert a definitive competitive
tier list.

### Team slot / roster item

Two small, Team-Builder-specific patterns:
- `.team-slot` — a bordered card (filled) or dashed placeholder (`.empty`)
  representing one of the team's 6 roster positions.
- `.roster-item` — a horizontal row (sprite, name, usage/win-rate/speed
  sub-text, Add button) in the scrollable "Legal pool" picker list.

## Representing Pokémon

Every dashboard view that names a specific Pokémon must show its sprite
alongside its name wherever there's room for one (table row, chart axis,
tooltip, team slot, roster picker row) — see "Sprite / icon cell" and
"Chart" above. A name-only Pokémon reference should only appear where
space genuinely doesn't allow an image (e.g. a `<select>` option's text).
Sprites come from Bulbagarden Archives via `pokemon_asset.csv`
(`docs/dashboard.md`'s "Icon sources"); a Pokémon with no resolvable sprite
degrades to text-only, never a broken image.

### Pokémon name formatting: camelCase

Display names are **camelCase**, derived from `pokemon_key` (PokéAPI's own
form slug, e.g. `landorus-therian`, `charizard-mega-x`) via
`pipelines/dashboard/data.py`'s `to_camel_case()`:

```
landorus-therian    -> landorusTherian
charizard-mega-x    -> charizardMegaX
great-tusk           -> greatTusk
urshifu-rapid-strike -> urshifuRapidStrike
porygon-z            -> porygonZ
```

This is computed once, server-side, when the dashboard payload is built
(`load_pokemon_names()`), so every consumer — KPI cards, every mart's
`pokemon_name` field, every `<select>` option — gets the identical string;
`app.js` never reformats a name itself.

Two things worth calling out about this choice:

- It's deliberately derived from **`pokemon_key`/`form_name`, not the raw
  `pokemon_name` column** in `data/normalized/pokemon.csv`. That column is
  the species-only name from PokéAPI (e.g. `landorus` for both
  Landorus-Incarnate and Landorus-Therian) — using it directly would make
  every alternate form of a species display identically and collide in
  any per-Pokémon list, table, or filter. Deriving from the form slug
  instead is what actually makes every legal Pokémon/form uniquely
  and correctly named.
- camelCase (not Title Case with spaces, e.g. "Landorus Therian") is a
  deliberate, explicit convention for this dashboard, not an
  accident of using the raw slug. It keeps names compact in dense table
  cells and select options and gives every name a single unambiguous
  rendering with no hyphen/space/case inconsistency to normalize per
  view.

### Ordering convention

Pokémon-keyed lists default to **descending order by their most relevant
ranking metric**, not alphabetical — usage count/share for usage-oriented
views, win rate for win-rate-oriented views, speed for the Speed Tiers
view. This applies to: the Usage leaders and Win rate leaders tables, the
Usage/Speed bar charts (top 15–20 by that metric), and Team Builder's
"Legal pool" picker (sortable between Usage / Win rate / Speed, all
descending).

The one deliberate exception: the plain `<select>` filter dropdowns (Build,
Moves, Team Cores tabs' Pokémon picker) stay **alphabetical**
(`distinctSorted()` in `app.js`) — for a dropdown a user is scanning to
find one specific Pokémon by name, alphabetical is more findable than
ranked; ranking only matters once you're looking at a list of *multiple*
Pokémon compared against each other.

### Percentage usage

Raw usage counts are supplemented with **usage share** —
`pokemon_usage_summary.usage_share`, a Pokémon's fraction of total roster
appearances within its `event_tier` partition (overall or a specific
tier) — computed in dbt (`sum(usage_count) over (partition by
event_tier)`), not client-side, so overall and per-tier shares stay
consistent with each other. Displayed as a percentage (`formatPercent()`
in `app.js`) next to the raw count wherever usage is shown: the "Most
Used" KPI card, the Usage leaders table, and Team Builder's roster picker
sub-text.

## Team Builder

A fully client-side (no backend, nothing uploaded) roster-assembly tool
(`setupTeamBuilder()` in `app.js`), built on the new
`pokemon_champions_profile` mart (one row per currently-legal Pokémon with
Champions-format stats plus usage/win-rate). A visitor searches/sorts the
legal pool, adds up to 6 to a team, and sees:

- their picks as filled **team slots** (empty slots shown as dashed
  placeholders).
- a **speed order** list — their own picks, fastest-first, each tagged
  with its Speed-tier badge (see above) — this is the practical payoff of
  having both Team Builder and Speed Tiers pull from the same
  `pokemon_champions_profile` mart: a team's speed order is just that
  mart filtered to the selected keys.
- a **summary row** (`.stat-summary-row`) of the team's average
  speed/usage share/win rate.

The team selection persists to `localStorage` (key
`pokemonChampionsTeamBuilder`) purely so a reload doesn't lose it — it is
never sent to a server or embedded in the published HTML; this stays true
to the dashboard's "static site, no backend" architecture
(`docs/dashboard.md`'s "Stack decision").

## Responsive behavior

Breakpoints match `docs/dashboard.md`'s existing convention: 720px (KPI
grid drops to 2 columns, chart height shrinks, Team Builder's two-column
grid collapses to one column and its team-slot grid drops to 2 columns)
and 480px (KPI cards stack vertically, filter selects go full-width).
Tables scroll horizontally inside `.table-scroll` rather than reflowing —
this is existing, unchanged convention, kept for the two new leaderboard
tables and the Speed Tiers table.

## Backlog: not yet buildable

Two explicitly-requested capabilities aren't in this pass because the
underlying data doesn't exist in this dataset yet — adding them as a
frontend-only feature would mean fabricating data, which this repo's
"provenance is mandatory" convention (`CLAUDE.md`) rules out:

- **Type-effectiveness / head-to-head matchups.** No in-scope source
  (PokéAPI, OP.GG, MunchStats, PokéBase, Bulbagarden) publishes Pokémon
  *types*, and MunchStats reports team rosters and a team's aggregate
  win/loss record, not individual battle outcomes against a named
  opponent — so there's no real signal for "what does Pokémon X lose to"
  or "who typically beats Pokémon Y." Building this for real needs either
  a new type-data source (e.g. PokéAPI's own `/type` endpoints, which
  *are* available and could close the type half of this gap in a future
  pass) or a battle-log source neither currently in scope nor deferred
  source (Limitless VGC, Victory Road) is confirmed to provide. Tracked in
  `docs/todo.md`'s M6 backlog.
- **Sortable table columns.** Already tracked in `docs/todo.md`'s existing
  M6 backlog entry; the new Usage leaders and Speed Tiers tables inherit
  the same fixed-sort limitation as the pre-existing tables and should get
  sortable headers in the same follow-up pass, not a bespoke one-off.

See `docs/todo.md`'s M6 backlog section for the full, current list
(regulation/date filters, the Streamlit dynamic-dashboard idea, etc.) —
this document only calls out the two items directly relevant to this
pass's design-system/Pokémon-representation scope.
