-- Gate: duplicate primary-key violations must equal 0 (docs/dataset-spec.md).
-- pokemon_asset_key is the composite `<pokemon_key>::<image_kind>`, so this
-- asserts one row per Pokémon *per image kind* — pokemon_key alone is
-- deliberately non-unique here now (see pokemon_asset.sql).
{{ config(meta={'category': 'duplicate_key', 'table_name': 'pokemon_asset', 'primary_key': 'pokemon_asset_key'}) }}
select pokemon_asset_key, count(*) as row_count
from {{ ref('pokemon_asset') }}
group by pokemon_asset_key
having count(*) > 1
