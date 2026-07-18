-- Time-sliced legal status for the Champions pool, from OP.GG rows mapped
-- to pokemon_key/pokemon_id by int_opgg_champions_mapped. regulation_code
-- is passed through as-is (currently always null: OP.GG's Champions
-- Pokédex page doesn't publish regulation codes — a known risk documented
-- in data/staging/opgg_champions.schema.json — so this table's null-rate
-- gate is expected to fail until a regulation-code source is added).
select
  resolved_pokemon_key || '::' || cast(extracted_at_utc as date) as legality_snapshot_key,
  resolved_pokemon_key as pokemon_key,
  resolved_pokemon_id as pokemon_id,
  regulation_code,
  is_legal,
  cast(extracted_at_utc as date) as snapshot_date,
  source_name,
  source_url,
  source_record_id,
  extracted_at_utc,
  dataset_version
from {{ ref('int_opgg_champions_mapped') }}
