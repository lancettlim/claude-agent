-- Gate: duplicate primary-key violations must equal 0 (docs/dataset-spec.md).
{{ config(meta={'category': 'duplicate_key', 'table_name': 'ability_detail', 'primary_key': 'ability_name'}) }}
select ability_name, count(*) as row_count
from {{ ref('ability_detail') }}
group by ability_name
having count(*) > 1
