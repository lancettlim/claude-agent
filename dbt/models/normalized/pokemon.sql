-- STUB: typed, empty output matching data/normalized/pokemon.schema.json.
-- Phase 2 (Normalization) replaces this with real identity-resolution logic
-- joining stg_pokeapi, stg_opgg_champions, and stg_munchstats on pokemon_id/
-- form_name. See docs/dataset-spec.md's "pokemon" entity definition.
select
  cast(null as varchar) as pokemon_key,
  cast(null as integer) as pokemon_id,
  cast(null as varchar) as pokemon_name,
  cast(null as varchar) as form_name,
  cast(null as varchar) as source_name,
  cast(null as varchar) as source_url,
  cast(null as varchar) as source_record_id,
  cast(null as varchar) as extracted_at_utc,
  cast(null as varchar) as dataset_version
where false
