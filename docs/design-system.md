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
| `--panel-dark` | `#12131a` | Broadcast color-block section/page header background (see "Broadcast color-block header" below) |
| `--accent-red` / `--accent-red-bg` | `#e3323c` / `#fce7e8` | Broadcast accent: active tab, ranked-list leader bar, Archetype Explorer's selected card |
| `--accent-gold` | `#f4b942` | Broadcast accent: reserved for #1-rank/MVP highlighting |

Speed-tier colors (`--speed-blazing`, `--speed-fast`, `--speed-average`,
`--speed-slow`, each with a `-bg` pair) are documented under "Speed-tier
badge" below rather than here, since they're paired directly with the
bucketing thresholds.

### Icon size scale

Three tokens replace what used to be four ad-hoc pixel values scattered
across the stylesheet/JS (40px KPI sprite, 32px roster picker, 24px table
cell, 22px chart axis):

| Token | Value | Use |
|---|---|---|
| `--icon-sm` | 32px | Table/list cells, ranked-list rows, speed-order rows (`ICON_SIZES.sm` in `app.js`) |
| `--icon-md` | 48px | Roster picker rows, Archetype Explorer member chips (`ICON_SIZES.md`) |
| `--icon-lg` | 72px | KPI hero sprite, team slot, Pokémon Profile hero, Overview spotlight card (`ICON_SIZES.lg`) |

**Every sprite/item/type image must use one of these three tokens** (or
the matching `ICON_SIZES` constant in JS) — no other pixel value. This is
a floor, not a ceiling: 32px is the smallest icon size anywhere in the
dashboard now, up from the previous 22–24px minimum.

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

- **`header`** — page title + generation timestamp, centered, white text on
  a `--panel-dark` color-blocked background (the broadcast/esports theme's
  most visible landmark — see "Broadcast color-block header" below).
- **`main`** — centered content column, `max-width: 1100px`.
- **`.kpi-row`** — responsive grid of `.kpi-card`s (`auto-fit,
  minmax(200px, 1fr)`), always the first thing under the header.
- **`.tabs` / `.tab-btn` / `.tab-panel`** — client-side tab navigation
  (`app.js`'s `setupTabs`). Every dashboard view beyond the KPI row lives in
  a tab, not a scrolling section — this was a deliberate M6 redesign
  decision (see `docs/todo.md`'s "Dashboard full redesign" entry) to keep
  the page scannable as views are added. Current tabs: Overview, Usage,
  Pokémon Profile, Archetypes, Regulations, Speed Tiers, Team Builder.
- **`section` (`.tab-panel`)** — a bordered white card per tab, `h2` title
  rendered as a broadcast color-block header, optional `.controls` filter
  row, then ranked-list and/or table content.

## Component catalog

### KPI card

`.kpi-card`: a bordered white card with an optional `--icon-lg` (72px)
sprite, a `.label` (uppercase, muted, small), a `.value` (bold, large,
wraps rather than overflows for long names), and an optional `.sub`
(muted, small) for supporting detail like a percentage or date. Used only
in the top `.kpi-row` — don't reuse this class for in-tab summary stats;
use `.stat-summary-row .stat` instead (see Team Builder below), which is
denser and doesn't compete visually with the page-level KPIs.

### Leaderboard table

The recurring pattern for "top N Pokémon by some metric" (Usage leaders,
Win rate leaders, Speed Tiers, Archetype Explorer's member table): a
`<table>` inside `.table-scroll`, first column a `.badge.badge-rank`
(`#1`, `#2`, …), second column a `pokemonCell()`-rendered sprite+name,
remaining columns the metric(s). Columns with `<th class="sortable"
data-sort-key="...">` are click-to-sort (`makeSortableTable()` in
`app.js`, toggling ascending/descending, `▲`/`▼` indicator appended to the
active header) — every leaderboard table added since the broadcast
redesign uses this; a table's *default* order (before any header click)
is still descending by its primary relevance metric, per "Ordering
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
to render a Pokémon in a table cell: an `--icon-sm` (32px) sprite (from the
`sprites` map, keyed by `pokemon_key`) next to the display name, wrapped in
`.cell-with-icon`. `itemCell()` follows the same pattern for held items.
**Any new table or list that references a specific Pokémon should use
`pokemonCell()` (or `spriteImg()` directly for non-table contexts, as
Team Builder's roster list and team slots do) rather than rendering a bare
name** — see "Representing Pokémon" below.

### Ranked list (replaces bar charts)

`renderRankedList(container, rows, opts)` (in `app.js`) is the dashboard's
**only** data-visualization component — Chart.js and its CDN dependency
were removed entirely as part of the broadcast redesign (dashboard
"remove bar charts... focus on percentages" ask), a net simplification
since there's no longer a "chart library didn't load" degradation path to
handle. It renders a dependency-free `.ranked-row` list: rank number,
optional icon (`keyFn` → sprite lookup, or `iconFn` for a direct icon src
like a move-type icon), label, a `.ranked-bar-fill` bar whose width is
relative to the *largest* value among the rows being shown (not a fixed
0–100% scale — this is a ranked comparison, not an absolute gauge), and a
right-aligned value (`displayFn`). The #1 row gets `.is-leader`
(`--accent-red` fill instead of `--blue`). Used by: Overview's Top 12/30,
Usage's per-tier ranked list, Pokémon Profile's move/team-core lists, and
Speed Tiers' top-20 list. Any new "top N by metric" visual should use this
instead of introducing a new charting approach.

### Broadcast color-block header

Section (`<h2>`) and page (`<header>`) titles are uppercase, `font-weight:
800`, `letter-spacing: 0.04em`, white text on a `--panel-dark` bar — this,
plus the `--accent-red`/`--accent-gold` accent tokens, is what gives the
dashboard its broadcast/esports look (dashboard "more Pokémon-like
features" ask). Deliberately **not** a webfont change — the effect comes
entirely from color-blocking and weight/case, preserving the
dependency-free-page convention "Type scale" above already established.

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
- `.team-slot` — a bordered card (filled, `--icon-lg` sprite) or dashed
  placeholder (`.empty`) representing one of the team's 6 roster
  positions.
- `.roster-item` — a horizontal row (`--icon-md` sprite, name,
  usage/win-rate/speed sub-text, Add button) in the scrollable "Legal
  pool" picker list.

### Spotlight card (Overview "Top 12")

`.spotlight-card`: a bordered card with a rank badge, `--icon-lg` sprite,
name, and a one-line usage%/win-rate% sub-stat, laid out in
`.spotlight-grid` (`auto-fill, minmax(140px, 1fr)`). Denser than a KPI
card, meant for a grid of many at once rather than 3–4 headline stats.

### Archetype card

`.archetype-card`: a clickable card (`<button>`, `aria-pressed` toggled)
showing an archetype's name, member count, combined usage share, average
win rate, and up to 3 member sprites (`--icon-md`). Selecting a card
filters the member table below it (see "Leaderboard table"). Exactly one
card is selected at a time; the highest-combined-usage archetype is
selected by default on tab load. **Always paired with the disclaimer
copy** in `index.html.jinja` making clear archetype membership is curated
editorial judgment (`dbt/seeds/archetype_pokemon_map.csv`), not sourced
tournament data — never present an archetype grouping as an extracted
signal.

### Gallery card (Pro Team Gallery)

`.gallery-card`: a bordered card wrapping a pre-rendered team-card PNG
(`pipelines/render/`, see `docs/dashboard.md`'s "Pro Team Gallery"
section) plus a caption (player name, country, event, placement,
archetype tag) and a "Load into my builder" button that copies the
gallery team's Pokémon into the Team Builder roster above it. Laid out in
`.gallery-grid` (`auto-fill, minmax(220px, 1fr)`), inside the Team
Builder tab but visually and functionally distinct from the roster
planner above it — this is a separate, read-only reference feature and
is never itself labeled "Team Builder."

## Representing Pokémon

Every dashboard view that names a specific Pokémon must show its sprite
alongside its name wherever there's room for one (table row, chart axis,
tooltip, team slot, roster picker row) — see "Sprite / icon cell" and
"Chart" above. A name-only Pokémon reference should only appear where
space genuinely doesn't allow an image (e.g. a `<select>` option's text).
Sprites come from Bulbagarden Archives via `pokemon_asset.csv`
(`docs/dashboard.md`'s "Icon sources"); a Pokémon with no resolvable sprite
degrades to text-only, never a broken image.

### Pokémon name formatting: PascalCase

Display names are **PascalCase**, derived from `pokemon_key` (PokéAPI's own
form slug, e.g. `landorus-therian`, `charizard-mega-x`) via
`pipelines/dashboard/data.py`'s `to_pascal_case()`:

```
landorus-therian    -> LandorusTherian
charizard-mega-x    -> CharizardMegaX
great-tusk           -> GreatTusk
urshifu-rapid-strike -> UrshifuRapidStrike
porygon-z            -> PorygonZ
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
- PascalCase (not Title Case with spaces, e.g. "Landorus Therian") is a
  deliberate, explicit convention for this dashboard, not an
  accident of using the raw slug. It keeps names compact in dense table
  cells and select options and gives every name a single unambiguous
  rendering with no hyphen/space/case inconsistency to normalize per
  view — while still reading as a proper noun (capitalized first letter),
  unlike a strict camelCase rendering would.

### Ordering convention

Pokémon-keyed lists default to **descending order by their most relevant
ranking metric**, not alphabetical — usage share for usage-oriented views,
win rate for win-rate-oriented views, speed for the Speed Tiers view. This
applies to every Pokémon-keyed list in the dashboard: leaderboard tables,
ranked lists, Team Builder's "Legal pool" picker (sortable between Usage /
Win rate / Speed, all descending) — **and now every Pokémon-picker
`<select>` dropdown too** (Pokémon Profile's picker), via
`distinctSortedByMetric()` in `app.js`, which orders by descending
`usage_share`.

This supersedes an earlier version of this convention that kept plain
`<select>` dropdowns alphabetical for findability — the dashboard has no
alphabetical Pokémon lists anywhere now; the ranked order is treated as
more useful than alphabetical scanning even in a dropdown. Non-Pokémon
selects (tournament tier) are unaffected and keep `distinctSorted()`'s
natural/alphabetical order, since there's no usage-relevance ranking that
applies to a tier name.

### Percentages, not raw counts

The dashboard shows **percentages/shares, not raw counts**, wherever a
share metric exists (dashboard "focus on percentages" ask):
`pokemon_usage_summary.usage_share`, `pokemon_build_usage.build_share`,
`pokemon_move_usage.move_share`, `pokemon_team_core_usage.partner_share`,
`archetype_summary.combined_usage_share`/`avg_win_rate` — all computed in
dbt (a `sum(x) over (partition by ...)` window function per mart), not
client-side, so shares stay internally consistent. Raw `usage_count`,
`total_wins`/`total_losses`, and `co_occurrence_count` are no longer
displayed anywhere in the UI (they still exist in the underlying CSVs for
ranking/testing purposes).

The one deliberate exception is **win rate's sample size**: hiding
`record_count` entirely risked a 100% win rate on a single recorded match
reading as more authoritative than a well-established Pokémon's 51% on
thousands of matches, so the Win rate leaders table and its `record_count`
filter (see below) keep a small `(n=X)` annotation next to the percentage
— a minimum-record-count filter, not a raw-count column. Base stats
(Speed, HP, Attack, etc. on the Pokémon Profile tab) aren't percentages
and are unaffected by this convention — they're numbers with no
"share of a whole" meaning to convert to.

### Filters beyond Pokémon/tier

Beyond the pre-existing tournament-tier filter (Usage tab), two more
filters were added: a **minimum recorded matches** threshold (Win rate
leaders table, `#win-rate-min-record-count-filter`, options 5/10/20/50 —
the same `RECORD_COUNT_FLOOR` idea `compute_kpis()`'s KPI card already
used, now user-adjustable) and the archetype/regulation dimensions
exposed as their own tabs (Archetype Explorer, Regulation Comparison)
rather than as `<select>` filters on existing tabs, since neither
dimension applies to the marts those existing tabs are built from.

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

Below the roster planner, the same tab also hosts the **Pro Team
Gallery** (see "Gallery card" above and `docs/dashboard.md`'s "Pro Team
Gallery" section) — a read-only reference feature, unrelated to and
visually distinct from the roster planner, never itself called "Team
Builder."

## Responsive behavior

Breakpoints match `docs/dashboard.md`'s existing convention: 720px (KPI
grid drops to 2 columns, chart height shrinks, Team Builder's two-column
grid collapses to one column and its team-slot grid drops to 2 columns)
and 480px (KPI cards stack vertically, filter selects go full-width).
Tables scroll horizontally inside `.table-scroll` rather than reflowing —
this is existing, unchanged convention, kept for the two new leaderboard
tables and the Speed Tiers table.

## Backlog: not yet buildable

One explicitly-requested capability still isn't in this pass because the
underlying data doesn't exist in this dataset yet — adding it as a
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
- **Date-range filtering / trend charts.** Only one `snapshot_date` exists
  in the data so far, so a date-range control would have nothing to range
  over — see `docs/dashboard.md`'s "Removed sections" for the same
  degenerate-data reasoning applied to the earlier legal-pool-trend
  section. Tracked in `docs/todo.md`.

Sortable table columns (previously listed here as backlog) are now
shipped — see "Leaderboard table" above.

See `docs/todo.md`'s M6 backlog section for the full, current list — this
document only calls out the items directly relevant to this pass's
design-system/Pokémon-representation scope.
