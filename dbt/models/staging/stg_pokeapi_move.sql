-- Passthrough of the raw PokéAPI move-detail staging snapshot.
select * from {{ source('staging', 'pokeapi_move') }}
