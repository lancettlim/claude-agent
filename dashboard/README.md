# Dashboard prototypes (M6 / M6.1)

Two prototypes for `docs/prd.md`'s M6 milestone ("Launch first-party
analytics dashboard views on top of v1 dataset outputs") and its still-open
question ("Which dashboard tool stack and hosting model should be used for
Phase 1?"). Both read exclusively from `data/marts/*.csv` (plus
`dashboard/game_data.py`'s static game-mechanic constants — a type chart,
type colors, and a weather/terrain-setting ability list, none of it
sourced/extracted data) and cover the same views:

- KPI overview cards (legal-pool size, most-used Pokémon, highest win
  rate, top stat gainer)
- Trend charts (legal-pool size by regulation, usage by tournament tier)
- **Speed Tier List** — all legal Pokémon by base speed (explicitly
  Champions-format base speed; no EVs/nature/items modeled anywhere in
  this dataset)
- **Stat Comparison** ("stats matching") — pick two Pokémon, compare all
  six stats + BST as paired bars, plus a type-effectiveness readout
- **Speed Control** — Choice Scarf users, Tailwind setters, Trick Room
  setters
- **Weather/Terrain Setters** — ranked by usage
- **Meta Tier List** — sortable usage-rank + win-rate table (no invented
  letter grades)
- Pokémon drill-down (top items/abilities, top moves, top team cores, top
  Tera types, win-rate proxy) with images and type badges

See `docs/todo.md`'s "M6.1 — VGC player-focused dashboard features"
section for the full checklist and what's backlogged (a full team-builder
type-matchup calculator, a damage calculator, real EV-adjusted speed
benchmarks, item/move icon sprites, historical trend lines).

## Prototype A — Streamlit (`streamlit_app.py`)

```
make dashboard-streamlit
# or: uv run streamlit run dashboard/streamlit_app.py
```

A live Python server that reads the marts CSVs with pandas on every
request (cached via `@st.cache_data`). Pros: fastest to extend (pure
Python, no HTML/CSS/JS), built-in widgets, matches the repo's existing
Python/uv stack. Cons: needs a running process — hosting means picking a
Python host (e.g. Streamlit Community Cloud, a container, an internal VM);
not a static artifact you can just hand someone a link to.

## Prototype B — static HTML (`build_static.py` → `static/index.html`)

```
make dashboard-static
# or: uv run python dashboard/build_static.py
```

A generator script that bakes `data/marts/*.csv` into a single
self-contained HTML file (data embedded as JSON, vanilla JS renders the
bars/tables/filters client-side — no chart library, no server, no
external requests). `static/index.html` is gitignored, like
`data/normalized/*.csv` and `data/marts/*.csv` — it's a build output,
regenerate it after any `make dbt-build`. Pros: zero hosting cost (any
static file host, or open the file directly), trivially shareable, no
Python process to keep running. Cons: every new view is hand-written
HTML/CSS/JS instead of a widget call; the whole dataset ships to the
client (currently ~1MB baked in).

## Status

Resolved (see `docs/todo.md`'s M6 section and `docs/prd.md`'s open
questions): **both are kept**, each for a different audience — Streamlit
for internal/exploratory use, static HTML for shareable snapshots —
rather than picking one winner. Still open: a real hosting target for
either, beyond local `make dashboard-streamlit`/`make dashboard-static`;
revisit when there's an actual deployment need.
