{{ config(location='../data/marts/pokemon_build_usage.csv') }}
-- Item/ability drill-down (docs/todo.md's Phase 3 tier/record/item
-- follow-up item; docs/prd.md's "Drill-down by Pokémon, team core, move,
-- and item usage"): usage count per Pokémon x item x ability combination,
-- restricted to the current legal pool and to roster slots that reported
-- at least one of item/ability.
--
-- build_share is usage_count's fraction of that Pokémon's own total build
-- rows (dashboard "percentages, not raw counts" ask), the same
-- share-of-own-total pattern pokemon_usage_summary.usage_share and
-- pokemon_move_usage.move_share use.
with counted as (
  select
    member.pokemon_key,
    member.item_name,
    member.ability,
    count(*) as usage_count
  from {{ ref('tournament_team_member') }} member
  inner join {{ ref('pokemon_stat_champions') }} champions
    on champions.pokemon_key = member.pokemon_key
    and champions.is_legal = true
  where member.item_name is not null
    or member.ability is not null
  group by member.pokemon_key, member.item_name, member.ability
)
select
  pokemon_key,
  item_name,
  ability,
  usage_count,
  round(
    usage_count::double / sum(usage_count) over (partition by pokemon_key),
    4
  ) as build_share,
  row_number() over (
    partition by pokemon_key
    order by usage_count desc
  ) as usage_rank
from counted
order by pokemon_key, usage_count desc
