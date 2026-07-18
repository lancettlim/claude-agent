-- Normalized tournament metadata from MunchStats: one row per event_id.
-- event_name/event_date/source_name/source_url are constant across a given
-- event's roster rows in stg_munchstats, so distinct collapses them safely.
select distinct
  event_id,
  event_name,
  event_date,
  source_name,
  source_url,
  event_id as source_record_id,
  extracted_at_utc,
  dataset_version
from {{ ref('int_munchstats_deduped') }}
