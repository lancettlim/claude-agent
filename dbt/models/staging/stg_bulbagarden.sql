-- Passthrough of the raw Bulbagarden Champions-menu-sprite staging
-- snapshot. Populated via pipelines/extract/bulbagarden.py.
select * from {{ source('staging', 'bulbagarden') }}
