-- Gate: duplicate primary-key violations must equal 0 (docs/dataset-spec.md).
select item_name, count(*) as row_count
from {{ ref('item_detail') }}
group by item_name
having count(*) > 1
