{{ config(location='../data/marts/pokemon_team_core_usage.csv') }}
-- Team-core drill-down (docs/prd.md's "Drill-down by Pokémon, team core,
-- move, and item usage"): usage count per unordered pair of Pokémon that
-- appeared on the same tournament team together, restricted to pairs where
-- both members are in the current legal pool. pokemon_key_a < pokemon_key_b
-- keeps each pair to a single row instead of both orderings.
select
  a.pokemon_key as pokemon_key_a,
  b.pokemon_key as pokemon_key_b,
  count(*) as usage_count
from {{ ref('tournament_team_member') }} a
inner join {{ ref('tournament_team_member') }} b
  on a.team_id = b.team_id
  and a.pokemon_key < b.pokemon_key
inner join {{ ref('pokemon_stat_champions') }} champions_a
  on champions_a.pokemon_key = a.pokemon_key
  and champions_a.is_legal = true
inner join {{ ref('pokemon_stat_champions') }} champions_b
  on champions_b.pokemon_key = b.pokemon_key
  and champions_b.is_legal = true
group by a.pokemon_key, b.pokemon_key
order by usage_count desc
