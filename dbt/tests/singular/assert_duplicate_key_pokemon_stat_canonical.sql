-- Gate: duplicate primary-key violations must equal 0 (docs/dataset-spec.md).
select pokemon_stat_canonical_key, count(*) as row_count
from {{ ref('pokemon_stat_canonical') }}
group by pokemon_stat_canonical_key
having count(*) > 1
