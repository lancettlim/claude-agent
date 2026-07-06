-- Gate: required-field null rate must be <=1% (docs/dataset-spec.md).
{{ config(fail_calc='max(null_rate)', error_if='>0.01', warn_if='>0.01') }}
select
  case when count(*) = 0 then 0.0 else (
    sum(case when pokemon_stat_champions_key is null then 1 else 0 end) +
    sum(case when pokemon_key is null then 1 else 0 end) +
    sum(case when pokemon_id is null then 1 else 0 end) +
    sum(case when hp is null then 1 else 0 end) +
    sum(case when attack is null then 1 else 0 end) +
    sum(case when defense is null then 1 else 0 end) +
    sum(case when sp_attack is null then 1 else 0 end) +
    sum(case when sp_defense is null then 1 else 0 end) +
    sum(case when speed is null then 1 else 0 end) +
    sum(case when stat_total is null then 1 else 0 end) +
    sum(case when is_legal is null then 1 else 0 end) +
    sum(case when source_name is null then 1 else 0 end) +
    sum(case when source_url is null then 1 else 0 end) +
    sum(case when source_record_id is null then 1 else 0 end) +
    sum(case when extracted_at_utc is null then 1 else 0 end) +
    sum(case when dataset_version is null then 1 else 0 end)
  )::double / (count(*) * 16)
  end as null_rate
from {{ ref('pokemon_stat_champions') }}
