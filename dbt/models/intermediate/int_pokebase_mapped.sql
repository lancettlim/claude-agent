-- Resolves each stg_pokebase row to a pokemon_key/pokemon_id via the
-- pokebase_slug_to_pokeapi_form seed. Most PokéBase slugs already equal a
-- real PokéAPI form_name directly (PokéBase's slug convention matches
-- PokéAPI's own); the seed's remaining entries are the same class of
-- "bare species with no default-equals-species-name PokéAPI form" gap
-- solved for OP.GG/MunchStats (e.g. "lycanroc" -> "lycanroc-midday").
-- Rows that resolve to no seed entry are dropped: per dataset-spec.md,
-- "Rows that cannot be mapped to a stable pokemon_key may remain in
-- staging but must not ship in release outputs without an explicit
-- confidence override."
select
  source.*,
  pokemon.pokemon_key as resolved_pokemon_key,
  pokemon.pokemon_id as resolved_pokemon_id
from {{ ref('stg_pokebase') }} source
inner join {{ ref('pokebase_slug_to_pokeapi_form') }} seed_map
  on seed_map.pokebase_slug = source.form_name
inner join {{ ref('pokemon') }} pokemon
  on pokemon.form_name = seed_map.pokeapi_form_name
