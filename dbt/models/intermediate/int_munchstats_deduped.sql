-- MunchStats occasionally records the same team (same team_id/roster)
-- twice within an event under two different placement numbers — observed
-- for 9 teams as of this snapshot, likely a day-1-standing vs.
-- final-standing scrape collision upstream. Keeps the lower (better)
-- placement's row set per team_id/slot_number so tournament_team and
-- tournament_team_member agree on exactly one placement per team; this is
-- a documented known limitation, not a guess at which record is "real".
select
  * exclude (_dedup_rank)
from (
  select
    *,
    row_number() over (
      partition by team_id, slot_number
      order by placement asc, event_id asc
    ) as _dedup_rank
  from {{ ref('stg_munchstats') }}
)
where _dedup_rank = 1
