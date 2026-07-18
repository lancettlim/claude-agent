-- Gate: >=90% of tournament records mapped to normalized team tables (docs/dataset-spec.md).
-- With zero staged rows this is vacuously not failed (pending Phase 1 MunchStats extraction).
-- fail_calc must resolve to an integer (dbt's run-results schema requires it), so this
-- reports coverage in basis points (100% = 10000 bps); pipelines/validate/report.py
-- divides by 10000 to recover the ratio for the report's metric_value.
{{ config(fail_calc='max(coverage_bps)', error_if='<9000', warn_if='<9000') }}
select
  case
    when count(*) = 0 then 10000
    else round((
      select count(*) from {{ ref('tournament_team_member') }}
    )::double / count(*) * 10000)::integer
  end as coverage_bps
from {{ source('staging', 'munchstats') }}
