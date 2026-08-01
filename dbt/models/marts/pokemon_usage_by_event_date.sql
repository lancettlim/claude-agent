{{ config(location='../data/marts/pokemon_usage_by_event_date.csv') }}
-- Usage over time from tournament_event.event_date (backlog.md #6): real
-- meta-over-time WITHOUT waiting on Blocker A (multi-snapshot extraction
-- history) -- events already carry dates spanning the tournament history,
-- so usage trends can be computed across events rather than across
-- extraction snapshots. Semantically distinct from a snapshot-date trend:
-- this shows how usage shifted across tournaments actually played, not
-- across when this dataset happened to be re-extracted.
--
-- usage_share/usage_rank are computed within each event_date partition
-- (mirroring pokemon_usage_summary's event_tier partitioning), so a
-- Pokémon's share reflects its standing among that date's tournaments
-- specifically.
with counted as (
  select
    member.pokemon_key,
    event.event_date,
    count(*) as usage_count
  from {{ ref('tournament_team_member') }} member
  inner join {{ ref('pokemon_stat_champions') }} champions
    on champions.pokemon_key = member.pokemon_key
    and champions.is_legal = true
  inner join {{ ref('tournament_event') }} event
    on event.event_id = member.event_id
  where event.event_date is not null
  group by member.pokemon_key, event.event_date
)
select
  pokemon_key,
  event_date,
  usage_count,
  round(
    usage_count::double / sum(usage_count) over (partition by event_date),
    4
  ) as usage_share,
  row_number() over (partition by event_date order by usage_count desc) as usage_rank
from counted
order by event_date, usage_count desc
