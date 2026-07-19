{{ config(location='../data/marts/pokemon_win_rate_summary.csv') }}
-- Win-rate-proxy KPI (docs/todo.md's Phase 3 tier/record/item follow-up
-- item; docs/prd.md's "KPI overview cards (usage, win-rate proxies, ...)"):
-- aggregates each team's reported win/loss record across every roster slot
-- that included the Pokémon, restricted to the current legal pool and to
-- teams MunchStats actually reported a record for.
select
  member.pokemon_key,
  sum(team.record_wins) as total_wins,
  sum(team.record_losses) as total_losses,
  round(
    sum(team.record_wins)::double
      / nullif(sum(team.record_wins) + sum(team.record_losses), 0),
    4
  ) as win_rate,
  count(*) as record_count
from {{ ref('tournament_team_member') }} member
inner join {{ ref('tournament_team') }} team
  on team.team_id = member.team_id
inner join {{ ref('pokemon_stat_champions') }} champions
  on champions.pokemon_key = member.pokemon_key
  and champions.is_legal = true
where team.record_wins is not null
  and team.record_losses is not null
group by member.pokemon_key
order by win_rate desc
