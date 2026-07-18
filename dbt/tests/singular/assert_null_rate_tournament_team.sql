-- Gate: required-field null rate must be <=1% (docs/dataset-spec.md).
{{ config(fail_calc='max(null_rate_bps)', error_if='>100', warn_if='>100') }}
select
  case when count(*) = 0 then 0 else round((
    sum(case when team_id is null then 1 else 0 end) +
    sum(case when event_id is null then 1 else 0 end) +
    sum(case when player_id is null then 1 else 0 end) +
    sum(case when placement is null then 1 else 0 end) +
    sum(case when source_name is null then 1 else 0 end) +
    sum(case when source_url is null then 1 else 0 end) +
    sum(case when source_record_id is null then 1 else 0 end) +
    sum(case when extracted_at_utc is null then 1 else 0 end) +
    sum(case when dataset_version is null then 1 else 0 end)
  )::double / (count(*) * 9) * 10000)::integer
  end as null_rate_bps
from {{ ref('tournament_team') }}
