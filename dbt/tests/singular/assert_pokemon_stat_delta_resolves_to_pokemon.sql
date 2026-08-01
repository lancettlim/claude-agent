-- Gate: pokemon_stat_* rows must resolve to pokemon (docs/dataset-spec.md).
{{ config(meta={'category': 'referential_integrity', 'check_name': 'pokemon_stat_delta_resolves_to_pokemon'}) }}
select child.pokemon_stat_delta_key
from {{ ref('pokemon_stat_delta') }} child
left join {{ ref('pokemon') }} parent on child.pokemon_key = parent.pokemon_key
where parent.pokemon_key is null
