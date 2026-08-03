-- Gate: required-field null rate must be <=1% (docs/dataset-spec.md).
-- Only genuinely required fields are counted. team_id_2/player_id_2 are
-- excluded because a bye has no opponent at all, and winner_team_id because
-- a tie and a bye have no winning team -- those are real, documented shapes
-- (see data/staging/rk9_pairings.schema.json), not missing data.
{{ config(fail_calc='max(null_rate_bps)', error_if='>100', warn_if='>100', meta={'category': 'null_rate', 'table_name': 'tournament_match'}) }}
select
  case when count(*) = 0 then 0 else round((
    sum(case when match_id is null then 1 else 0 end) +
    sum(case when event_id is null then 1 else 0 end) +
    sum(case when division is null then 1 else 0 end) +
    sum(case when round_number is null then 1 else 0 end) +
    sum(case when outcome is null then 1 else 0 end) +
    sum(case when source_name is null then 1 else 0 end) +
    sum(case when source_url is null then 1 else 0 end) +
    sum(case when source_record_id is null then 1 else 0 end) +
    sum(case when extracted_at_utc is null then 1 else 0 end) +
    sum(case when dataset_version is null then 1 else 0 end)
  )::double / (count(*) * 10) * 10000)::integer
  end as null_rate_bps
from {{ ref('tournament_match') }}
