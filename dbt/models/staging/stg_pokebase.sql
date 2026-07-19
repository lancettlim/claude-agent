-- Passthrough of the raw PokéBase staging snapshot. Fills in
-- data/staging/pokebase.csv via pipelines/extract/pokebase.py.
select * from {{ source('staging', 'pokebase') }}
