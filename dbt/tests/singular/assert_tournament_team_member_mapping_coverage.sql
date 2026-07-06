-- Gate: >=90% of tournament records mapped to normalized team tables (docs/dataset-spec.md).
-- With zero staged rows this is vacuously 1.0 (pending Phase 1 MunchStats extraction).
{{ config(fail_calc='max(coverage_ratio)', error_if='<0.90', warn_if='<0.90') }}
select
  case when count(*) = 0 then 1.0
    else (
      select count(*) from {{ ref('tournament_team_member') }}
    )::double / count(*)
  end as coverage_ratio
from {{ source('staging', 'munchstats') }}
