-- Time-sliced, regulation-aware legal status for the Champions pool, from
-- PokéBase rows mapped to pokemon_key/pokemon_id by int_pokebase_mapped.
-- PokéBase (not OP.GG) is the source here because it's the only in-scope
-- source that publishes real regulation codes per Pokémon (OP.GG's
-- Champions Pokédex page has a single regulation-agnostic legal pool,
-- with regulation_code always null — see pokemon_stat_champions.sql,
-- which still uses OP.GG for Champions-format stats and overall legality).
select
  resolved_pokemon_key || '::' || regulation_code || '::' || cast(extracted_at_utc as date)
    as legality_snapshot_key,
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
from {{ ref('int_pokebase_mapped') }}
