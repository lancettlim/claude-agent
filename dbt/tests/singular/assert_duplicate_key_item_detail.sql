-- Gate: duplicate primary-key violations must equal 0 (docs/dataset-spec.md).
{{ config(meta={'category': 'duplicate_key', 'table_name': 'item_detail', 'primary_key': 'item_name'}) }}
select item_name, count(*) as row_count
from {{ ref('item_detail') }}
group by item_name
having count(*) > 1
