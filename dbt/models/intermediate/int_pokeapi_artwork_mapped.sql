-- Resolves each stg_pokeapi_artwork row to a pokemon_key/pokemon_id.
--
-- Unlike every other *_mapped model in this layer, this one needs no
-- mapping seed: the artwork manifest's form_name is PokéAPI's own form
-- slug, which is exactly what `pokemon.form_name`/`pokemon_key` already
-- is. The cross-source name-reconciliation problem the seeds exist to
-- solve (OP.GG's "mega-charizard-x" vs PokéAPI's "charizard-mega-x")
-- simply doesn't arise when both sides are PokéAPI.
--
-- The inner join still matters: it enforces the same rule as the seeded
-- models, that a row which resolves to no canonical `pokemon` row is
-- dropped rather than shipped (docs/dataset-spec.md — "Rows that cannot be
-- mapped to a stable pokemon_key may remain in staging but must not ship
-- in release outputs"). It is also what keeps pokemon_asset's
-- referential-integrity gate satisfied by construction.
select
  source.*,
  pokemon.pokemon_key as resolved_pokemon_key,
  pokemon.pokemon_id as resolved_pokemon_id
from {{ ref('int_pokeapi_artwork_latest') }} source
inner join {{ ref('pokemon') }} pokemon
  on pokemon.form_name = source.form_name
