-- Image manifest for Pokémon/form references — see docs/dataset-spec.md's
-- "pokemon_asset" entity definition.
--
-- Two image kinds, one row each per pokemon_key:
--   * menu_sprite (Bulbagarden Archives, 128x128) — the dense-UI asset,
--     correct at table-cell size.
--   * home_render (PokéAPI sprite repository, 512x512) — the hero asset,
--     added because upscaling a 128px menu sprite into the dashboard's
--     96px/128px hero slots visibly blurs, worse again on HiDPI.
--
-- This is why the primary key is `<pokemon_key>::<image_kind>` rather than
-- bare pokemon_key: v1 scoped this entity to one menu sprite per form, and
-- a second kind per form makes pokemon_key alone non-unique. pokemon_key
-- stays the join key to every other entity.
with menu_sprite as (
  select
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
),

home_render as (
  select
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
  from {{ ref('int_pokeapi_artwork_mapped') }}
),

combined as (
  select * from menu_sprite
  union all
  select * from home_render
)

select
  pokemon_key || '::' || image_kind as pokemon_asset_key,
  pokemon_key,
  pokemon_id,
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
from combined
