-- Gate: duplicate primary-key violations must equal 0 (docs/dataset-spec.md).
select team_member_id, count(*) as row_count
from {{ ref('tournament_team_member') }}
group by team_member_id
having count(*) > 1
