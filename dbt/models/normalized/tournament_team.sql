-- Team-level tournament metadata from MunchStats: one row per team_id.
-- event_id/player_id/player_name/player_country/placement/source fields
-- are constant across a given team's roster rows in stg_munchstats, so
-- distinct collapses them safely. player_country is optional -- not every
-- MunchStats player row reports it.
select distinct
  team_id,
  event_id,
  player_id,
  player_name,
  player_country,
  placement,
  record_wins,
  record_losses,
  source_name,
  source_url,
  team_id as source_record_id,
  extracted_at_utc,
  dataset_version
from {{ ref('int_munchstats_deduped') }}
