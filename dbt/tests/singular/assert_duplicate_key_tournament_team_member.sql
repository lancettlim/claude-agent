-- Gate: duplicate primary-key violations must equal 0 (docs/dataset-spec.md).
{{ config(meta={'category': 'duplicate_key', 'table_name': 'tournament_team_member', 'primary_key': 'team_member_id'}) }}
select team_member_id, count(*) as row_count
from {{ ref('tournament_team_member') }}
group by team_member_id
having count(*) > 1
