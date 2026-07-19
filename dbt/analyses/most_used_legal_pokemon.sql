-- Example query (docs/dataset-spec.md's "Validate example analysis
-- queries" release-readiness item): the 20 most-used Pokémon across all
-- MunchStats tournament rosters, restricted to the current OP.GG legal
-- pool.
select
  member.pokemon_key,
  count(*) as usage_count
from {{ ref('tournament_team_member') }} member
inner join {{ ref('pokemon_stat_champions') }} champions
  on champions.pokemon_key = member.pokemon_key
  and champions.is_legal = true
group by member.pokemon_key
order by usage_count desc
limit 20
