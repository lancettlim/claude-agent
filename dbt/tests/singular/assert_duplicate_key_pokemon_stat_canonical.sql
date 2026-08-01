-- Gate: duplicate primary-key violations must equal 0 (docs/dataset-spec.md).
{{ config(meta={'category': 'duplicate_key', 'table_name': 'pokemon_stat_canonical', 'primary_key': 'pokemon_stat_canonical_key'}) }}
select pokemon_stat_canonical_key, count(*) as row_count
from {{ ref('pokemon_stat_canonical') }}
group by pokemon_stat_canonical_key
having count(*) > 1
