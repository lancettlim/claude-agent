-- Gate: legality_snapshot rows must resolve to pokemon (docs/dataset-spec.md).
select child.legality_snapshot_key
from {{ ref('legality_snapshot') }} child
left join {{ ref('pokemon') }} parent on child.pokemon_key = parent.pokemon_key
where parent.pokemon_key is null
