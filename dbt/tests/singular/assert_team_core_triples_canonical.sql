{{ config(meta={'category': 'mart_quality', 'table_name': 'pokemon_team_core_triple_usage'}) }}
-- A triple must have exactly one canonical ordering. Any row returned here
-- would allow mirrored duplicates into counts and archetype detection.
select *
from {{ ref('pokemon_team_core_triple_usage') }}
where not (pokemon_key_a < pokemon_key_b and pokemon_key_b < pokemon_key_c)
