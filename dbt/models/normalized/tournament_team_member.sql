-- One row per Pokémon on a normalized tournament team, mapping
-- stg_munchstats.pokemon_name to pokemon_key/pokemon_id via the
-- munchstats_name_to_pokeapi_form seed (dataset-spec.md's MunchStats
-- mapping rule: "Map roster Pokémon names to canonical pokemon_id and
-- pokemon_key"). Rows whose name doesn't resolve are dropped — per
-- dataset-spec.md, unmapped rows must not ship in release outputs.
select
  source.source_record_id as team_member_id,
  source.team_id,
  source.event_id,
  pokemon.pokemon_key,
  pokemon.pokemon_id,
  source.slot_number,
  source.item_name,
  source.ability,
  source.tera_type,
  source.moves,
  source.source_name,
  source.source_url,
  source.source_record_id,
  source.extracted_at_utc,
  source.dataset_version
from {{ ref('int_munchstats_deduped') }} source
inner join {{ ref('munchstats_name_to_pokeapi_form') }} seed_map
  on seed_map.munchstats_pokemon_name = source.pokemon_name
inner join {{ ref('pokemon') }} pokemon
  on pokemon.form_name = seed_map.pokeapi_form_name
