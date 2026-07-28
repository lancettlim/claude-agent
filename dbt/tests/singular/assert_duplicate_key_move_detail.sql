-- Gate: duplicate primary-key violations must equal 0 (docs/dataset-spec.md).
select move_name, count(*) as row_count
from {{ ref('move_detail') }}
group by move_name
having count(*) > 1
