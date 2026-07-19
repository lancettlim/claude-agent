{{ config(location='../data/marts/legality_summary_by_regulation.csv') }}
-- KPI card feed (docs/prd.md's "KPI overview cards ... legality changes";
-- docs/todo.md's "Document KPI views and filter dimensions (regulation/
-- date/...)"): current legal-pool size per regulation and snapshot date.
select
  regulation_code,
  snapshot_date,
  count(*) as legal_pokemon_count
from {{ ref('legality_snapshot') }}
where is_legal = true
group by regulation_code, snapshot_date
order by regulation_code
