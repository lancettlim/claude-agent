# Dashboard prototypes (M6)

Two prototypes for `docs/prd.md`'s M6 milestone ("Launch first-party
analytics dashboard views on top of v1 dataset outputs") and its still-open
question ("Which dashboard tool stack and hosting model should be used for
Phase 1?"). Both read exclusively from `data/marts/*.csv` and cover the
same views: KPI overview cards (legal-pool size, most-used Pokémon, highest
win rate, top stat gainer), trend charts (legal-pool size by regulation,
usage by tournament tier), and a Pokémon drill-down (top items/abilities,
top moves, top team cores, win-rate proxy).

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

Both are prototypes for comparison, not yet the committed answer to
`docs/prd.md`'s open question. See `docs/todo.md`'s M6 section for the
decision and next steps once one is chosen (or both are kept for
different audiences — e.g. static for a public snapshot link, Streamlit
for internal exploration).
