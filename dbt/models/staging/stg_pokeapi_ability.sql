-- Passthrough of the raw PokéAPI ability-detail staging snapshot.
select * from {{ source('staging', 'pokeapi_ability') }}
