-- Full history of raw PokéAPI move-detail staging snapshots. See
-- stg_pokeapi.sql's header for the snapshot_date/history-vs-latest design.
select
  *,
  cast(extracted_at_utc as date) as snapshot_date
from {{ source('staging', 'pokeapi_move') }}
