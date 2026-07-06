-- Passthrough of the raw MunchStats staging snapshot. Phase 1 fills in
-- data/staging/munchstats.csv via pipelines/extract/munchstats.py.
select * from {{ source('staging', 'munchstats') }}
