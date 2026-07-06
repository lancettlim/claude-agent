-- Gate: required-field null rate must be <=1% (docs/dataset-spec.md).
-- fail_calc override surfaces the computed rate itself (not a row count) as
-- run_results.json's "failures" value; see pipelines/validate/report.py.
{{ config(fail_calc='max(null_rate)', error_if='>0.01', warn_if='>0.01') }}
select
  case when count(*) = 0 then 0.0 else (
    sum(case when pokemon_key is null then 1 else 0 end) +
    sum(case when pokemon_id is null then 1 else 0 end) +
    sum(case when pokemon_name is null then 1 else 0 end) +
    sum(case when form_name is null then 1 else 0 end) +
    sum(case when source_name is null then 1 else 0 end) +
    sum(case when source_url is null then 1 else 0 end) +
    sum(case when source_record_id is null then 1 else 0 end) +
    sum(case when extracted_at_utc is null then 1 else 0 end) +
    sum(case when dataset_version is null then 1 else 0 end)
  )::double / (count(*) * 9)
  end as null_rate
from {{ ref('pokemon') }}
