{{ config(location='../data/marts/pokemon_item_usage.csv') }}
-- Item drill-down for the Pokémon Profile tab's dedicated Items section
-- (docs/design-system.md's "Item / Ability / Move separation" — split out
-- of the old combined pokemon_build_usage mart so items, abilities, and
-- moves each get their own ranked, capped-at-top-N view instead of one
-- undifferentiated build table): usage count and item_share (that count's
-- fraction of the Pokémon's own total item rows) per Pokémon x item,
-- restricted to the current legal pool, ranked within each Pokémon.
-- short_effect is joined from move_detail's sibling item_detail table
-- (PokéAPI item effect text) and nullable when that lookup didn't resolve.
with counted as (
  select
    member.pokemon_key,
    member.item_name,
    count(*) as usage_count
  from {{ ref('int_champions_roster') }} member
  inner join {{ ref('pokemon_stat_champions') }} champions
    on champions.pokemon_key = member.pokemon_key
    and champions.is_legal = true
  where member.item_name is not null
  group by member.pokemon_key, member.item_name
)
select
  counted.pokemon_key,
  counted.item_name,
  item_detail.short_effect,
  counted.usage_count,
  round(
    counted.usage_count::double / sum(counted.usage_count) over (partition by counted.pokemon_key),
    4
  ) as item_share,
  row_number() over (
    partition by counted.pokemon_key
    order by counted.usage_count desc
  ) as usage_rank
from counted
left join {{ ref('item_detail') }} item_detail
  on item_detail.item_name = counted.item_name
order by counted.pokemon_key, counted.usage_count desc
