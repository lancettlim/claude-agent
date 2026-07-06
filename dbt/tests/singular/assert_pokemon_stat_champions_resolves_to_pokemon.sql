-- Gate: pokemon_stat_* rows must resolve to pokemon (docs/dataset-spec.md).
select child.pokemon_stat_champions_key
from {{ ref('pokemon_stat_champions') }} child
left join {{ ref('pokemon') }} parent on child.pokemon_key = parent.pokemon_key
where parent.pokemon_key is null
