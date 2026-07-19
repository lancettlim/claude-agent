{{ config(location='../data/marts/pokemon_tera_type_usage.csv') }}
-- Tera type drill-down (VGC player-focused dashboard pass): usage count
-- per Pokémon x tera_type, restricted to the current legal pool and to
-- roster slots reporting a tera type. Mirrors pokemon_move_usage.sql's
-- structure; tournament_team_member.tera_type is already normalized but
-- wasn't surfaced by any mart until now.
select
  member.pokemon_key,
  member.tera_type,
  count(*) as usage_count,
  row_number() over (
    partition by member.pokemon_key
    order by count(*) desc
  ) as usage_rank
from {{ ref('tournament_team_member') }} member
inner join {{ ref('pokemon_stat_champions') }} champions
  on champions.pokemon_key = member.pokemon_key
  and champions.is_legal = true
where member.tera_type is not null
group by member.pokemon_key, member.tera_type
order by member.pokemon_key, usage_count desc
