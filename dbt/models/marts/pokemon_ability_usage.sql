{{ config(location='../data/marts/pokemon_ability_usage.csv') }}
-- Ability-only usage drill-down (VGC player-focused dashboard pass):
-- usage count per Pokémon x ability, restricted to the current legal
-- pool. Drops the item_name dimension pokemon_build_usage groups by, so
-- ability usage isn't fragmented across every item pairing — this powers
-- the Weather/Terrain setter view (filtering to a known ability list)
-- without re-aggregating pokemon_build_usage client-side in two separate
-- dashboard codebases.
select
  member.pokemon_key,
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
where member.ability is not null
group by member.pokemon_key, member.ability
order by member.pokemon_key, usage_count desc
