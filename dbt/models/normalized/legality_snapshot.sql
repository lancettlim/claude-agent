-- STUB: typed, empty output matching data/normalized/legality_snapshot.schema.json.
-- Phase 2 replaces this with real regulation-aware legality snapshot logic
-- sourced from stg_opgg_champions.
select
  cast(null as varchar) as legality_snapshot_key,
  cast(null as varchar) as pokemon_key,
  cast(null as integer) as pokemon_id,
  cast(null as varchar) as regulation_code,
  cast(null as boolean) as is_legal,
  cast(null as varchar) as snapshot_date,
  cast(null as varchar) as source_name,
  cast(null as varchar) as source_url,
  cast(null as varchar) as source_record_id,
  cast(null as varchar) as extracted_at_utc,
  cast(null as varchar) as dataset_version
where false
