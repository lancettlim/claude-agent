-- Gate: tournament_team_member rows must resolve to pokemon (docs/dataset-spec.md).
select child.team_member_id
from {{ ref('tournament_team_member') }} child
left join {{ ref('pokemon') }} parent on child.pokemon_key = parent.pokemon_key
where parent.pokemon_key is null
