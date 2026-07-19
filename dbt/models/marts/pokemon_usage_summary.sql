{{ config(location='../data/marts/pokemon_usage_summary.csv') }}
-- Flat analytical export (docs/todo.md's Phase 3 "Publish flat analytical
-- exports and summary aggregates" item): total tournament-roster usage per
-- Pokémon, restricted to the current legal pool, ranked descending.
select
  member.pokemon_key,
  count(*) as usage_count,
  row_number() over (order by count(*) desc) as usage_rank
from {{ ref('tournament_team_member') }} member
inner join {{ ref('pokemon_stat_champions') }} champions
  on champions.pokemon_key = member.pokemon_key
  and champions.is_legal = true
group by member.pokemon_key
