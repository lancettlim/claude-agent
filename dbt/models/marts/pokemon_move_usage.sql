{{ config(location='../data/marts/pokemon_move_usage.csv') }}
-- Move drill-down (docs/todo.md's Phase 3 tier/record/item follow-up item;
-- docs/prd.md's "Drill-down by Pokémon, team core, move, and item usage"):
-- usage count per Pokémon x move, unnesting tournament_team_member's
-- pipe-delimited moves list, restricted to the current legal pool and to
-- roster slots that reported a move list.
select
  member.pokemon_key,
  trim(move.move_name) as move_name,
  count(*) as usage_count,
  row_number() over (
    partition by member.pokemon_key
    order by count(*) desc
  ) as usage_rank
from {{ ref('tournament_team_member') }} member
inner join {{ ref('pokemon_stat_champions') }} champions
  on champions.pokemon_key = member.pokemon_key
  and champions.is_legal = true
, unnest(string_split(member.moves, '|')) as move(move_name)
where member.moves is not null
group by member.pokemon_key, trim(move.move_name)
order by member.pokemon_key, usage_count desc
