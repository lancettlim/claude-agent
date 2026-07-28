{{ config(location='../data/marts/pokemon_ability_usage.csv') }}
-- Ability drill-down for the Pokémon Profile tab's dedicated Ability
-- section (docs/design-system.md's "Item / Ability / Move separation" —
-- split out of the old combined pokemon_build_usage mart): usage count and
-- ability_share (that count's fraction of the Pokémon's own total ability
-- rows) per Pokémon x ability, restricted to the current legal pool,
-- ranked within each Pokémon. short_effect is joined from ability_detail
-- (PokéAPI ability effect text) and nullable when that lookup didn't
-- resolve.
with counted as (
  select
    member.pokemon_key,
    member.ability,
    count(*) as usage_count
  from {{ ref('tournament_team_member') }} member
  inner join {{ ref('pokemon_stat_champions') }} champions
    on champions.pokemon_key = member.pokemon_key
    and champions.is_legal = true
  where member.ability is not null
  group by member.pokemon_key, member.ability
)
select
  counted.pokemon_key,
  counted.ability,
  ability_detail.short_effect,
  counted.usage_count,
  round(
    counted.usage_count::double / sum(counted.usage_count) over (partition by counted.pokemon_key),
    4
  ) as ability_share,
  row_number() over (
    partition by counted.pokemon_key
    order by counted.usage_count desc
  ) as usage_rank
from counted
left join {{ ref('ability_detail') }} ability_detail
  on ability_detail.ability_name = counted.ability
order by counted.pokemon_key, counted.usage_count desc
