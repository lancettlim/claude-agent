-- Gate: tournament_team rows must resolve to tournament_event (docs/dataset-spec.md).
select child.team_id
from {{ ref('tournament_team') }} child
left join {{ ref('tournament_event') }} parent on child.event_id = parent.event_id
where parent.event_id is null
