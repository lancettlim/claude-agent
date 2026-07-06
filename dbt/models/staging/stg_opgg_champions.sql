-- Passthrough of the raw OP.GG Champions staging snapshot. Phase 1 fills in
-- data/staging/opgg_champions.csv via pipelines/extract/opgg.py.
select * from {{ source('staging', 'opgg_champions') }}
