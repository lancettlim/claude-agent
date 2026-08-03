-- Gate: team_list_member rows must resolve to pokemon (docs/dataset-spec.md).
{{ config(meta={'category': 'referential_integrity', 'check_name': 'team_list_member_resolves_to_pokemon'}) }}
select child.team_list_member_id
from {{ ref('team_list_member') }} child
left join {{ ref('pokemon') }} parent on child.pokemon_key = parent.pokemon_key
where parent.pokemon_key is null
