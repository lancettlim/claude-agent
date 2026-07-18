-- Canonical identity table for Pokémon and form references. See
-- docs/dataset-spec.md's "pokemon" entity definition.
--
-- PokéAPI is the sole source of identity rows: it's fetched with one row
-- per PokéAPI /pokemon list entry (base species plus every Mega/regional/
-- alternate form), so form_name is already the normalized, globally-unique
-- cross-source key described by dataset-spec.md's "pokemon_key is the
-- normalized cross-source identifier for one Pokémon/form record" — no
-- separate identity resolution against OP.GG/MunchStats is needed here;
-- those sources' rows are mapped onto this table in pokemon_stat_champions
-- and tournament_team_member instead.
select
  form_name as pokemon_key,
  pokemon_id,
  pokemon_name,
  form_name,
  source_name,
  source_url,
  source_record_id,
  extracted_at_utc,
  dataset_version
from {{ ref('stg_pokeapi') }}
