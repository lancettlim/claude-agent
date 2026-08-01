-- Gate: legality_snapshot rows must resolve to pokemon (docs/dataset-spec.md).
{{ config(meta={'category': 'referential_integrity', 'check_name': 'legality_snapshot_resolves_to_pokemon'}) }}
select child.legality_snapshot_key
from {{ ref('legality_snapshot') }} child
left join {{ ref('pokemon') }} parent on child.pokemon_key = parent.pokemon_key
where parent.pokemon_key is null
