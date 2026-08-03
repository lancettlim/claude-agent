-- Gate: required-field null rate must be <=1% (docs/dataset-spec.md).
-- item_name/ability/nature/moves are excluded: a published team list can
-- legitimately omit any of them (see data/staging/limitless.schema.json).
{{ config(fail_calc='max(null_rate_bps)', error_if='>100', warn_if='>100', meta={'category': 'null_rate', 'table_name': 'team_list_member'}) }}
select
  case when count(*) = 0 then 0 else round((
    sum(case when team_list_member_id is null then 1 else 0 end) +
    sum(case when team_list_id is null then 1 else 0 end) +
    sum(case when pokemon_key is null then 1 else 0 end) +
    sum(case when pokemon_id is null then 1 else 0 end) +
    sum(case when slot_number is null then 1 else 0 end) +
    sum(case when source_name is null then 1 else 0 end) +
    sum(case when source_url is null then 1 else 0 end) +
    sum(case when source_record_id is null then 1 else 0 end) +
    sum(case when extracted_at_utc is null then 1 else 0 end) +
    sum(case when dataset_version is null then 1 else 0 end)
  )::double / (count(*) * 10) * 10000)::integer
  end as null_rate_bps
from {{ ref('team_list_member') }}
