-- Gate: duplicate primary-key violations must equal 0 (docs/dataset-spec.md).
select pokemon_stat_champions_key, count(*) as row_count
from {{ ref('pokemon_stat_champions') }}
group by pokemon_stat_champions_key
having count(*) > 1
