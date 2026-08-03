{{ config(location='../data/marts/roster_source_agreement.csv') }}
-- Cross-source validation: for players covered by BOTH MunchStats and
-- Limitless at the same event, do the two sources report the same six
-- Pokémon? (backlog.md #26.)
--
-- This is the payoff of ingesting a second source for events that are
-- already covered. Until now every roster fact in this dataset came from a
-- single source with nothing to check it against; a silent upstream
-- regression in MunchStats' scraping would have been invisible.
--
-- The event join is real, not heuristic: Limitless' tournament page links
-- out to the same event on RK9, and MunchStats reuses RK9's event ids, so
-- rk9_event_id joins straight to tournament_event.event_id. (Names and
-- dates would not work -- the two sources agree on neither.) Players join
-- on name and country, the same basis int_rk9_mapped.sql uses.
--
-- Coverage is asymmetric by design: Limitless publishes only the day-2 cut,
-- so this compares that subset, not the full field. covered_players makes
-- the size of the comparison explicit rather than implying it spans the
-- event.
with limitless_teams as (
  select
    rk9_event_id as event_id,
    lower(trim(player_name)) as player_join_key,
    lower(trim(player_country)) as country_join_key,
    limitless_team_id,
    list_sort(list(distinct pokemon_key)) as pokemon_keys
  from {{ ref('int_limitless_mapped') }}
  where rk9_event_id <> ''
  group by rk9_event_id, lower(trim(player_name)), lower(trim(player_country)), limitless_team_id
),

munchstats_teams as (
  select
    team.event_id,
    lower(trim(team.player_name)) as player_join_key,
    lower(trim(team.player_country)) as country_join_key,
    team.team_id,
    list_sort(list(distinct member.pokemon_key)) as pokemon_keys
  from {{ ref('tournament_team') }} team
  inner join {{ ref('tournament_team_member') }} member
    on member.team_id = team.team_id
  group by team.event_id, lower(trim(team.player_name)), lower(trim(team.player_country)), team.team_id
),

matched as (
  select
    limitless_teams.event_id,
    limitless_teams.limitless_team_id,
    munchstats_teams.team_id,
    limitless_teams.pokemon_keys as limitless_keys,
    munchstats_teams.pokemon_keys as munchstats_keys,
    len(list_intersect(limitless_teams.pokemon_keys, munchstats_teams.pokemon_keys)) as shared_count,
    greatest(len(limitless_teams.pokemon_keys), len(munchstats_teams.pokemon_keys)) as roster_size
  from limitless_teams
  inner join munchstats_teams
    on munchstats_teams.event_id = limitless_teams.event_id
    and munchstats_teams.player_join_key = limitless_teams.player_join_key
    and munchstats_teams.country_join_key = limitless_teams.country_join_key
)

select
  event.event_id,
  event.event_name,
  count(*) as covered_players,
  sum(case when matched.shared_count = matched.roster_size then 1 else 0 end) as exact_agreement_players,
  round(
    sum(case when matched.shared_count = matched.roster_size then 1 else 0 end)::double / count(*),
    4
  ) as exact_agreement_rate,
  round(sum(matched.shared_count)::double / nullif(sum(matched.roster_size), 0), 4) as slot_agreement_rate
from matched
inner join {{ ref('tournament_event') }} event
  on event.event_id = matched.event_id
group by event.event_id, event.event_name
order by covered_players desc
