-- Gate: duplicate primary-key violations must equal 0 (docs/dataset-spec.md).
select pokemon_asset_key, count(*) as row_count
from {{ ref('pokemon_asset') }}
group by pokemon_asset_key
having count(*) > 1
