-- Gate: tournament_team_member rows must resolve to tournament_team (docs/dataset-spec.md).
select child.team_member_id
from {{ ref('tournament_team_member') }} child
left join {{ ref('tournament_team') }} parent on child.team_id = parent.team_id
where parent.team_id is null
