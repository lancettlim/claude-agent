-- Gate: duplicate primary-key violations must equal 0 (docs/dataset-spec.md).
select event_id, count(*) as row_count
from {{ ref('tournament_event') }}
group by event_id
having count(*) > 1
