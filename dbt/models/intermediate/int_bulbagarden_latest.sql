-- The current point-in-time stg_bulbagarden snapshot: filtered to its most
-- recent snapshot_date, so a multi-snapshot staging history (backlog.md
-- #1/#2) doesn't change downstream primary-key/referential-integrity
-- contracts. Full history stays queryable via stg_bulbagarden directly.
select *
from {{ ref('stg_bulbagarden') }}
where snapshot_date = (select max(snapshot_date) from {{ ref('stg_bulbagarden') }})
