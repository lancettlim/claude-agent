-- Gate: duplicate primary-key violations must equal 0 (docs/dataset-spec.md).
{{ config(meta={'category': 'duplicate_key', 'table_name': 'team_list_member', 'primary_key': 'team_list_member_id'}) }}
select team_list_member_id, count(*) as row_count
from {{ ref('team_list_member') }}
group by team_list_member_id
having count(*) > 1
