-- Canonical PokéAPI stat snapshot: one row per form, matching pokemon.sql's
-- pokemon_key (form_name) 1:1.
select
  form_name as pokemon_stat_canonical_key,
  form_name as pokemon_key,
  pokemon_id,
  hp,
  attack,
  defense,
  sp_attack,
  sp_defense,
  speed,
  stat_total,
  source_name,
  source_url,
  source_record_id,
  extracted_at_utc,
  dataset_version
from {{ ref('stg_pokeapi') }}
