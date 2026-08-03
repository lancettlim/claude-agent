-- Gate: team_list_member rows must resolve to team_list (docs/dataset-spec.md).
{{ config(meta={'category': 'referential_integrity', 'check_name': 'team_list_member_resolves_to_team_list'}) }}
select child.team_list_member_id
from {{ ref('team_list_member') }} child
left join {{ ref('team_list') }} parent on child.team_list_id = parent.team_list_id
where parent.team_list_id is null
