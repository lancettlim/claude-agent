-- Gate: duplicate primary-key violations must equal 0 (docs/dataset-spec.md).
select legality_snapshot_key, count(*) as row_count
from {{ ref('legality_snapshot') }}
group by legality_snapshot_key
having count(*) > 1
