-- STUB: typed, empty output matching data/normalized/pokemon_stat_delta.schema.json.
-- Phase 2 replaces this with real canonical-vs-Champions delta computation
-- joining pokemon_stat_canonical and pokemon_stat_champions.
select
  cast(null as varchar) as pokemon_stat_delta_key,
  cast(null as varchar) as pokemon_key,
  cast(null as integer) as pokemon_id,
  cast(null as integer) as hp_delta,
  cast(null as integer) as attack_delta,
  cast(null as integer) as defense_delta,
  cast(null as integer) as sp_attack_delta,
  cast(null as integer) as sp_defense_delta,
  cast(null as integer) as speed_delta,
  cast(null as integer) as stat_total_delta,
  cast(null as varchar) as canonical_dataset_version,
  cast(null as varchar) as champions_dataset_version,
  cast(null as varchar) as source_name,
  cast(null as varchar) as source_url,
  cast(null as varchar) as extracted_at_utc,
  cast(null as varchar) as dataset_version
where false
