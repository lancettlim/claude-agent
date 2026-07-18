-- Gate: required-field null rate must be <=1% (docs/dataset-spec.md).
{{ config(fail_calc='max(null_rate_bps)', error_if='>100', warn_if='>100') }}
select
  case when count(*) = 0 then 0 else round((
    sum(case when legality_snapshot_key is null then 1 else 0 end) +
    sum(case when pokemon_key is null then 1 else 0 end) +
    sum(case when pokemon_id is null then 1 else 0 end) +
    sum(case when regulation_code is null then 1 else 0 end) +
    sum(case when is_legal is null then 1 else 0 end) +
    sum(case when snapshot_date is null then 1 else 0 end) +
    sum(case when source_name is null then 1 else 0 end) +
    sum(case when source_url is null then 1 else 0 end) +
    sum(case when source_record_id is null then 1 else 0 end) +
    sum(case when extracted_at_utc is null then 1 else 0 end) +
    sum(case when dataset_version is null then 1 else 0 end)
  )::double / (count(*) * 11) * 10000)::integer
  end as null_rate_bps
from {{ ref('legality_snapshot') }}
