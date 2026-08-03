{{ config(location='../data/marts/top_tournament_teams.csv') }}
-- Top Teams tab's leaderboard feed (docs/design-system.md's "Top teams"
-- ask): one row per tournament_team with a reported win/loss record,
-- ranked by win_rate, with its event context and full roster (all
-- reported member Pokémon, not filtered to the current legal pool -- a
-- team's roster is a historical fact, and filtering members out would
-- misrepresent what was actually played). This is real, sourced
-- MunchStats data, distinct from the curated, hand-authored Pro Team
-- Gallery (data/reference_teams/reference_teams.json) the same tab also
-- surfaces -- see docs/dashboard.md's "Pro Team Gallery" section.
--
-- Capped to the top 100 by win_rate (`limit 100` below): MunchStats
-- reports tens of thousands of individual teams, but the dashboard only
-- ever surfaces the top ~18 in a .grid-6xn tile grid with no table tier
-- underneath (docs/design-system.md's "Top Teams" section) -- shipping
-- every team into the page's baked-in JSON (window.DASHBOARD_DATA) would
-- bloat every visitor's page load for rows nothing in the UI ever reads.
-- 100 leaves headroom for a future detail-table tier without the
-- unbounded-row-count cost.
with member_rosters as (
  select
    team_id,
    string_agg(pokemon_key, '|' order by slot_number) as pokemon_keys
  from {{ ref('int_champions_roster') }}
  group by team_id
)
select
  team.team_id,
  event.event_name,
  event.event_tier,
  event.event_date,
  team.player_name,
  team.player_country,
  team.placement,
  team.record_wins,
  team.record_losses,
  round(
    team.record_wins::double / nullif(team.record_wins + team.record_losses, 0),
    4
  ) as win_rate,
  roster.pokemon_keys,
  row_number() over (order by team.record_wins::double / nullif(team.record_wins + team.record_losses, 0) desc) as team_rank
from {{ ref('tournament_team') }} team
inner join {{ ref('tournament_event') }} event
  on event.event_id = team.event_id
inner join member_rosters roster
  on roster.team_id = team.team_id
where team.record_wins is not null
  and team.record_losses is not null
  and (team.record_wins + team.record_losses) > 0
order by win_rate desc
limit 100
