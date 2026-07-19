{{ config(location='../data/marts/pokemon_build_usage.csv') }}
-- Item/ability drill-down (docs/todo.md's Phase 3 tier/record/item
-- follow-up item; docs/prd.md's "Drill-down by Pokémon, team core, move,
-- and item usage"): usage count per Pokémon x item x ability combination,
-- restricted to the current legal pool and to roster slots that reported
-- at least one of item/ability.
select
  member.pokemon_key,
  member.item_name,
  member.ability,
  count(*) as usage_count,
  row_number() over (
    partition by member.pokemon_key
    order by count(*) desc
  ) as usage_rank
from {{ ref('tournament_team_member') }} member
inner join {{ ref('pokemon_stat_champions') }} champions
  on champions.pokemon_key = member.pokemon_key
  and champions.is_legal = true
where member.item_name is not null
  or member.ability is not null
group by member.pokemon_key, member.item_name, member.ability
order by member.pokemon_key, usage_count desc
