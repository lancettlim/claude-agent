-- Gate: duplicate primary-key violations must equal 0 (docs/dataset-spec.md).
{{ config(meta={'category': 'duplicate_key', 'table_name': 'pokemon_asset', 'primary_key': 'pokemon_asset_key'}) }}
select pokemon_asset_key, count(*) as row_count
from {{ ref('pokemon_asset') }}
group by pokemon_asset_key
having count(*) > 1
