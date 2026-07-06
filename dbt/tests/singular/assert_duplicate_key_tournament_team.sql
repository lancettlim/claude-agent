-- Gate: duplicate primary-key violations must equal 0 (docs/dataset-spec.md).
select team_id, count(*) as row_count
from {{ ref('tournament_team') }}
group by team_id
having count(*) > 1
