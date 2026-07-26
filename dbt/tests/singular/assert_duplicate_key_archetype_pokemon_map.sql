-- Gate: duplicate (archetype_key, pokemon_key) pairs must equal 0 --
-- catches accidental double-entry in the curated seed, not a ban on one
-- Pokémon belonging to multiple *different* archetypes (docs/seeds/schema.yml).
select archetype_key, pokemon_key, count(*) as row_count
from {{ ref('archetype_pokemon_map') }}
group by archetype_key, pokemon_key
having count(*) > 1
