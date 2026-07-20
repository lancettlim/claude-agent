-- Resolves each stg_bulbagarden row to a pokemon_key/pokemon_id via the
-- bulbagarden_title_to_pokeapi_form seed (docs/dataset-spec.md's
-- Bulbagarden mapping rule). Rows that resolve to no seed entry are
-- dropped: per dataset-spec.md, "Rows that cannot be mapped to a stable
-- pokemon_key may remain in staging but must not ship in release outputs
-- without an explicit confidence override."
with resolved as (
  select
    source.*,
    pokemon.pokemon_key as resolved_pokemon_key,
    pokemon.pokemon_id as resolved_pokemon_id
  from {{ ref('stg_bulbagarden') }} source
  inner join {{ ref('bulbagarden_title_to_pokeapi_form') }} seed_map
    on seed_map.bulbagarden_title = source.bulbagarden_title
  inner join {{ ref('pokemon') }} pokemon
    on pokemon.form_name = seed_map.pokeapi_form_name
)

-- A handful of species (Vivillon's wing patterns, Florges's colors,
-- Furfrou's trims, Alcremie's cream flavors, Pyroar's cosmetic female
-- sprite) have many visually distinct Bulbagarden titles but only one
-- PokéAPI form/variety, so multiple rows here resolve to the same
-- pokemon_key. Keep the unsuffixed/base title deterministically, mirroring
-- int_opgg_champions_mapped.sql's cosmetic-duplicate dedup.
select
  * exclude (_dedup_rank)
from (
  select
    *,
    row_number() over (
      partition by resolved_pokemon_key
      order by (
        case when bulbagarden_title like '%-%.png' then 1 else 0 end
      )
    ) as _dedup_rank
  from resolved
)
where _dedup_rank = 1
