-- Champions-format stat snapshot from OP.GG, mapped to pokemon_key/
-- pokemon_id by int_opgg_champions_mapped.
select
  resolved_pokemon_key || '-champions' as pokemon_stat_champions_key,
  resolved_pokemon_key as pokemon_key,
  resolved_pokemon_id as pokemon_id,
  hp,
  attack,
  defense,
  sp_attack,
  sp_defense,
  speed,
  stat_total,
  is_legal,
  source_name,
  source_url,
  source_record_id,
  extracted_at_utc,
  dataset_version
from {{ ref('int_opgg_champions_mapped') }}
