-- One row per canonical Limitless team list: a team *composition* identity,
-- independent of who played it and where.
--
-- This is what Limitless has that MunchStats does not (backlog.md #26).
-- MunchStats mints a fresh team_id per player per event, so the same six
-- Pokémon fielded by two players read as two unrelated teams. Limitless
-- assigns one id to the composition itself and reuses it, which makes
-- "how many players ran this exact team, and how did it do" answerable for
-- the first time.
--
-- Scope, stated plainly: Limitless publishes team lists for the day-2 cut
-- only (156 of 1,096 players at NAIC 2026), so this covers top-cut teams,
-- not the full field. It is not a broader view of the same events than
-- MunchStats gives -- it is a narrower one with sharper identity.
select
  limitless_team_id as team_list_id,
  count(distinct tournament_id) as tournament_count,
  -- limitless_player_id arrives as an integer via DuckDB's CSV type
  -- detection, so it needs an explicit cast before it can fall back to the
  -- player's name for a standings row that carried no player link.
  count(distinct coalesce(nullif(cast(limitless_player_id as varchar), ''), player_name))
    as player_count,
  min(placement) as best_placement,
  min(tournament_date) as first_seen_date,
  min(tournament_id) as first_seen_tournament_id,
  max(rk9_event_id) as first_seen_event_id,
  max(regulation_set) as regulation_set,
  max(source_name) as source_name,
  max(source_url) as source_url,
  limitless_team_id as source_record_id,
  max(extracted_at_utc) as extracted_at_utc,
  max(dataset_version) as dataset_version
from {{ ref('int_limitless_mapped') }}
group by limitless_team_id
