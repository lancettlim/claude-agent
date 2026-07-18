-- Gate: >=95% of OP.GG legal pool mapped to canonical pokemon_id (docs/dataset-spec.md).
-- With zero staged rows this is vacuously not failed (pending Phase 1 OP.GG extraction).
-- fail_calc must resolve to an integer (dbt's run-results schema requires it), so this
-- reports coverage in basis points (100% = 10000 bps); pipelines/validate/report.py
-- divides by 10000 to recover the ratio for the report's metric_value.
{{ config(fail_calc='max(coverage_bps)', error_if='<9500', warn_if='<9500') }}
select
  case
    when count(*) = 0 then 10000
    else round(sum(case when pokemon_id is not null then 1 else 0 end)::double / count(*) * 10000)::integer
  end as coverage_bps
from {{ source('staging', 'opgg_champions') }}
where is_legal = true
