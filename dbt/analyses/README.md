# Example Analyses

dbt "analyses" are compiled (`dbt compile`) but not materialized or run by
`dbt build`/`dbt test` — they exist to prove the modeled tables actually
support the example queries `docs/dataset-spec.md`'s "Validate example
analysis queries" release-readiness item calls for.

- `top_stat_gainers_losers.sql` — largest Champions-vs-canonical stat
  changes. Validated against the current snapshot: every mapped Pokémon
  currently has a `stat_total_delta` of exactly 0 — OP.GG's Champions
  stats are identical to PokéAPI's canonical base stats for every row in
  this snapshot. That's the real data, not a query bug (spot-checked
  `pokemon_stat_canonical`/`pokemon_stat_champions` directly); it means
  this snapshot predates any Champions-format rebalance, or none has
  happened yet. The query itself is ready to surface real deltas once one
  does.
- `most_used_legal_pokemon.sql` — validated; produces a real, non-degenerate
  usage ranking (e.g. Incineroar/Gholdengo/Sneasler lead the current
  snapshot).
- `largest_legal_pool_changes_by_regulation.sql` — validated but currently
  degenerate: `regulation_code` is now real (sourced from PokéBase, see
  `docs/dataset-spec.md`), but this dataset has only been extracted once so
  far, so there's no second `snapshot_date` yet to diff against (`docs/
  backlog.md`'s "Blocker A"). The query is structurally correct and ready
  once multiple snapshots accumulate in production.

Run with, e.g.:

```
dbt compile --select most_used_legal_pokemon
```

then execute the compiled SQL in `target/compiled/pokemon_champions/analyses/`
against `dbt/data/warehouse.duckdb`.
