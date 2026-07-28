-- Passthrough of the raw PokéAPI item-detail staging snapshot.
select * from {{ source('staging', 'pokeapi_item') }}
