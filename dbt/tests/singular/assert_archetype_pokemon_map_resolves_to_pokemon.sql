-- Gate: every archetype_pokemon_map row must resolve to pokemon --
-- catches typos in the curated seed's pokemon_key column.
select child.archetype_key, child.pokemon_key
from {{ ref('archetype_pokemon_map') }} child
left join {{ ref('pokemon') }} parent on child.pokemon_key = parent.pokemon_key
where parent.pokemon_key is null
