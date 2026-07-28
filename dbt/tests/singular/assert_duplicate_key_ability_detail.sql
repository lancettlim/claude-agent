-- Gate: duplicate primary-key violations must equal 0 (docs/dataset-spec.md).
select ability_name, count(*) as row_count
from {{ ref('ability_detail') }}
group by ability_name
having count(*) > 1
