{{ config(location='../data/marts/pokemon_move_usage.csv') }}
-- Move drill-down (docs/todo.md's Phase 3 tier/record/item follow-up item;
-- docs/prd.md's "Drill-down by Pokémon, team core, move, and item usage"):
-- usage count per Pokémon x move, unnesting tournament_team_member's
-- pipe-delimited moves list, restricted to the current legal pool and to
-- roster slots that reported a move list.
--
-- move_share is usage_count's fraction of that Pokémon's own total move
-- rows (dashboard "percentages, not raw counts" ask), the same
-- share-of-own-total pattern pokemon_usage_summary.usage_share and
-- pokemon_build_usage.build_share use.
with counted as (
  select
    member.pokemon_key,
    trim(move.move_name) as move_name,
    count(*) as usage_count
  from {{ ref('tournament_team_member') }} member
  inner join {{ ref('pokemon_stat_champions') }} champions
    on champions.pokemon_key = member.pokemon_key
    and champions.is_legal = true
  , unnest(string_split(member.moves, '|')) as move(move_name)
  where member.moves is not null
  group by member.pokemon_key, trim(move.move_name)
)
select
  pokemon_key,
  move_name,
  usage_count,
  round(
    usage_count::double / sum(usage_count) over (partition by pokemon_key),
    4
  ) as move_share,
  row_number() over (
    partition by pokemon_key
    order by usage_count desc
  ) as usage_rank
from counted
order by pokemon_key, usage_count desc
