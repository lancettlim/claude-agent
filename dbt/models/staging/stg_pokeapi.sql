-- Full history of raw PokéAPI staging snapshots: every retained
-- date-partitioned CSV under data/staging/pokeapi/ (see pipelines/cli.py's
-- snapshot retention), unioned by DuckDB's CSV glob reader, with
-- snapshot_date as a groupable dimension (backlog.md #2). Downstream
-- normalized models consume int_pokeapi_latest instead of this model
-- directly, so they stay pinned to the current point-in-time snapshot.
select
  *,
  cast(extracted_at_utc as date) as snapshot_date
from {{ source('staging', 'pokeapi') }}
