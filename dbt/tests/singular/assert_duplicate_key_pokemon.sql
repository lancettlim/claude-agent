-- Gate: duplicate primary-key violations must equal 0 (docs/dataset-spec.md).
-- Default fail_calc (count(*)) = number of pokemon_key values with >1 row.
{{ config(meta={'category': 'duplicate_key', 'table_name': 'pokemon', 'primary_key': 'pokemon_key'}) }}
select pokemon_key, count(*) as row_count
from {{ ref('pokemon') }}
group by pokemon_key
having count(*) > 1
