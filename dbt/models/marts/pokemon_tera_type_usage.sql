{{ config(location='../data/marts/pokemon_tera_type_usage.csv') }}
-- Tera type drill-down (backlog.md #10: "Tera type is a defining format
-- mechanic and is entirely absent from the analytics layer"): usage count
-- and tera_share (that count's fraction of the Pokémon's own total
-- tera-type rows) per Pokémon x tera_type, restricted to the current legal
-- pool, ranked within each Pokémon -- the same share-of-own-total pattern
-- pokemon_item_usage.item_share/pokemon_ability_usage.ability_share use.
-- tera_type coverage is partial (dbt/models/marts/schema.yml's existing
-- optional-field caveat): MunchStats doesn't report it for every roster
-- slot, so this only covers the subset that did.
with counted as (
  select
    member.pokemon_key,
    member.tera_type,
    count(*) as usage_count
  from {{ ref('tournament_team_member') }} member
  inner join {{ ref('pokemon_stat_champions') }} champions
    on champions.pokemon_key = member.pokemon_key
    and champions.is_legal = true
  where member.tera_type is not null
  group by member.pokemon_key, member.tera_type
)
select
  pokemon_key,
  tera_type,
  usage_count,
  round(
    usage_count::double / sum(usage_count) over (partition by pokemon_key),
    4
  ) as tera_share,
  row_number() over (
    partition by pokemon_key
    order by usage_count desc
  ) as usage_rank
from counted
order by pokemon_key, usage_count desc
