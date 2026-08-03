{{ config(location='../data/marts/pokemon_matchup_summary.csv') }}
-- One row per Pokémon: its best and worst head-to-head matchups, plus its
-- overall record across every decided match its teams played.
--
-- Built on pokemon_head_to_head, and inherits that mart's team-vs-team
-- caveat exactly (see its header): "best matchup" means the opponent
-- Pokémon whose teams this Pokémon's teams beat most reliably, not a
-- claim about the two Pokémon fighting each other.
--
-- Best/worst are chosen by Wilson lower bound over a minimum sample, not
-- raw win rate: with min_matches at 1 the extremes are always 100%/0% over
-- a single match, which is noise rather than a matchup.
{% set min_matches = 10 %}
with qualified as (
  select *
  from {{ ref('pokemon_head_to_head') }}
  where matches_played >= {{ min_matches }}
),

ranked as (
  select
    *,
    row_number() over (
      partition by pokemon_key
      order by wilson_lower_bound desc, matches_played desc, opponent_pokemon_key asc
    ) as best_rank,
    row_number() over (
      partition by pokemon_key
      order by wilson_lower_bound asc, matches_played desc, opponent_pokemon_key asc
    ) as worst_rank
  from qualified
),

overall as (
  select
    pokemon_key,
    sum(matches_played) as total_matchup_appearances,
    count(*) as distinct_opponents,
    round(sum(wins)::double / nullif(sum(matches_played), 0), 4) as overall_win_rate
  from {{ ref('pokemon_head_to_head') }}
  group by pokemon_key
)

select
  overall.pokemon_key,
  overall.overall_win_rate,
  overall.distinct_opponents,
  overall.total_matchup_appearances,
  best.opponent_pokemon_key as best_matchup_pokemon_key,
  best.win_rate as best_matchup_win_rate,
  best.matches_played as best_matchup_matches,
  worst.opponent_pokemon_key as worst_matchup_pokemon_key,
  worst.win_rate as worst_matchup_win_rate,
  worst.matches_played as worst_matchup_matches,
  {{ min_matches }} as min_matches_threshold
from overall
left join ranked as best
  on best.pokemon_key = overall.pokemon_key
  and best.best_rank = 1
left join ranked as worst
  on worst.pokemon_key = overall.pokemon_key
  and worst.worst_rank = 1
order by overall.total_matchup_appearances desc, overall.pokemon_key
