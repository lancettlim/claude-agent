-- Example query (docs/dataset-spec.md's "Validate example analysis
-- queries" release-readiness item): day-over-day change in legal-pool size
-- per regulation, ranked by magnitude.
--
-- Known limitations this query currently runs into (see docs/todo.md):
-- 1) OP.GG's Champions Pokédex page doesn't publish regulation codes, so
--    every legality_snapshot row currently has regulation_code = null —
--    real per-regulation breakdowns need a regulation-code source added.
-- 2) Change requires two or more snapshot_dates; this dataset has only
--    been extracted once so far, so `previous_legal_count`/`change` are
--    null for every row until a second extraction run lands. The query
--    is structurally ready for that once both gaps close.
with legal_counts_by_day as (
  select
    regulation_code,
    snapshot_date,
    count(*) filter (where is_legal) as legal_count
  from {{ ref('legality_snapshot') }}
  group by regulation_code, snapshot_date
),

with_change as (
  select
    regulation_code,
    snapshot_date,
    legal_count,
    lag(legal_count) over (
      partition by regulation_code order by snapshot_date
    ) as previous_legal_count,
    legal_count - lag(legal_count) over (
      partition by regulation_code order by snapshot_date
    ) as change
  from legal_counts_by_day
)

select *
from with_change
order by abs(change) desc nulls last
