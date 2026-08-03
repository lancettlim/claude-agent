-- Gate: tournament_match rows must resolve to tournament_event (docs/dataset-spec.md).
{{ config(meta={'category': 'referential_integrity', 'check_name': 'tournament_match_resolves_to_tournament_event'}) }}
select child.match_id
from {{ ref('tournament_match') }} child
left join {{ ref('tournament_event') }} parent on child.event_id = parent.event_id
where parent.event_id is null
