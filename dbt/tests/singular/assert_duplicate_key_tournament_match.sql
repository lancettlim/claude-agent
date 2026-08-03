-- Gate: duplicate primary-key violations must equal 0 (docs/dataset-spec.md).
{{ config(meta={'category': 'duplicate_key', 'table_name': 'tournament_match', 'primary_key': 'match_id'}) }}
select match_id, count(*) as row_count
from {{ ref('tournament_match') }}
group by match_id
having count(*) > 1
