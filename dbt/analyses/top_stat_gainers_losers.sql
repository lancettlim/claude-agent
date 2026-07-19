-- Example query (docs/dataset-spec.md's "Validate example analysis
-- queries" release-readiness item): the 15 largest Champions-format stat
-- buffs and nerfs relative to canonical PokéAPI base stats.
-- Run with `dbt compile` (this is a dbt analysis: compiled, not
-- materialized) or copy into a duckdb session against dbt/data/warehouse.duckdb.
with ranked as (
  select
    pokemon_key,
    stat_total_delta,
    row_number() over (order by stat_total_delta desc) as gainer_rank,
    row_number() over (order by stat_total_delta asc) as loser_rank
  from {{ ref('pokemon_stat_delta') }}
)

select pokemon_key, stat_total_delta, 'gainer' as direction
from ranked
where gainer_rank <= 15

union all

select pokemon_key, stat_total_delta, 'loser' as direction
from ranked
where loser_rank <= 15

order by direction, stat_total_delta desc
