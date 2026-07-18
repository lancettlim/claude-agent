-- Gate: required-field null rate must be <=1% (docs/dataset-spec.md).
{{ config(fail_calc='max(null_rate_bps)', error_if='>100', warn_if='>100') }}
select
  case when count(*) = 0 then 0 else round((
    sum(case when pokemon_stat_delta_key is null then 1 else 0 end) +
    sum(case when pokemon_key is null then 1 else 0 end) +
    sum(case when pokemon_id is null then 1 else 0 end) +
    sum(case when hp_delta is null then 1 else 0 end) +
    sum(case when attack_delta is null then 1 else 0 end) +
    sum(case when defense_delta is null then 1 else 0 end) +
    sum(case when sp_attack_delta is null then 1 else 0 end) +
    sum(case when sp_defense_delta is null then 1 else 0 end) +
    sum(case when speed_delta is null then 1 else 0 end) +
    sum(case when stat_total_delta is null then 1 else 0 end) +
    sum(case when canonical_dataset_version is null then 1 else 0 end) +
    sum(case when champions_dataset_version is null then 1 else 0 end) +
    sum(case when source_name is null then 1 else 0 end) +
    sum(case when source_url is null then 1 else 0 end) +
    sum(case when extracted_at_utc is null then 1 else 0 end) +
    sum(case when dataset_version is null then 1 else 0 end)
  )::double / (count(*) * 16) * 10000)::integer
  end as null_rate_bps
from {{ ref('pokemon_stat_delta') }}
