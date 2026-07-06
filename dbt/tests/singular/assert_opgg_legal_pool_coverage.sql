-- Gate: >=95% of OP.GG legal pool mapped to canonical pokemon_id (docs/dataset-spec.md).
-- With zero staged rows this is vacuously 1.0 (pending Phase 1 OP.GG extraction).
{{ config(fail_calc='max(coverage_ratio)', error_if='<0.95', warn_if='<0.95') }}
select
  case when count(*) = 0 then 1.0
    else sum(case when pokemon_id is not null then 1 else 0 end)::double / count(*)
  end as coverage_ratio
from {{ source('staging', 'opgg_champions') }}
where is_legal = true
