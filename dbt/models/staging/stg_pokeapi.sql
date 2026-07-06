-- Passthrough of the raw PokéAPI staging snapshot. Phase 1 fills in
-- data/staging/pokeapi.csv via pipelines/extract/pokeapi.py.
select * from {{ source('staging', 'pokeapi') }}
