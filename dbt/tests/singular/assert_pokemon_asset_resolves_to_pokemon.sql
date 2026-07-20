-- Gate: pokemon_asset rows must resolve to pokemon (docs/dataset-spec.md).
select child.pokemon_asset_key
from {{ ref('pokemon_asset') }} child
left join {{ ref('pokemon') }} parent on child.pokemon_key = parent.pokemon_key
where parent.pokemon_key is null
