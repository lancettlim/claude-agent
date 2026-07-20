-- Sprite/menu-icon image manifest for Pokémon/form references, sourced
-- from Bulbagarden Archives. One row per pokemon_key (v1 scope is one
-- menu sprite per form) — see docs/dataset-spec.md's "pokemon_asset"
-- entity definition.
select
  resolved_pokemon_key as pokemon_asset_key,
  resolved_pokemon_key as pokemon_key,
  resolved_pokemon_id as pokemon_id,
  image_kind,
  local_cache_path,
  sha1,
  width,
  height,
  source_name,
  source_url,
  source_record_id,
  extracted_at_utc,
  dataset_version
from {{ ref('int_bulbagarden_mapped') }}
