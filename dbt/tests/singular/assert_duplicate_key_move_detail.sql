-- Gate: duplicate primary-key violations must equal 0 (docs/dataset-spec.md).
{{ config(meta={'category': 'duplicate_key', 'table_name': 'move_detail', 'primary_key': 'move_name'}) }}
select move_name, count(*) as row_count
from {{ ref('move_detail') }}
group by move_name
having count(*) > 1
