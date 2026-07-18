-- Gate: required-field null rate must be <=1% (docs/dataset-spec.md).
-- fail_calc must resolve to an integer (dbt's run-results schema requires it), so this
-- reports the null rate in basis points (1% = 100 bps); pipelines/validate/report.py
-- divides by 10000 to recover the ratio for the report's metric_value.
{{ config(fail_calc='max(null_rate_bps)', error_if='>100', warn_if='>100') }}
select
  case when count(*) = 0 then 0 else round((
    sum(case when pokemon_key is null then 1 else 0 end) +
    sum(case when pokemon_id is null then 1 else 0 end) +
    sum(case when pokemon_name is null then 1 else 0 end) +
    sum(case when form_name is null then 1 else 0 end) +
    sum(case when source_name is null then 1 else 0 end) +
    sum(case when source_url is null then 1 else 0 end) +
    sum(case when source_record_id is null then 1 else 0 end) +
    sum(case when extracted_at_utc is null then 1 else 0 end) +
    sum(case when dataset_version is null then 1 else 0 end)
  )::double / (count(*) * 9) * 10000)::integer
  end as null_rate_bps
from {{ ref('pokemon') }}
