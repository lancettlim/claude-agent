{{ config(location='../data/marts/detected_archetype_candidates.csv') }}
-- Experimental, data-derived archetype anchors. A candidate must appear on
-- at least five real Champions teams, have above-chance three-way lift, and
-- have above-chance average pair lift. These are deliberately transparent
-- thresholds rather than an opaque clustering model.
--
-- Substantially overlapping candidates (two shared Pokemon) consolidate
-- under the strongest candidate in their one-hop neighbourhood. This keeps
-- near-identical triples from presenting as separate archetypes while
-- avoiding transitive chains that could collapse most of the metagame into
-- one giant community.
with eligible as (
  select
    'core-' || pokemon_key_a || '--' || pokemon_key_b || '--' || pokemon_key_c
      as candidate_key,
    *,
    ln(1 + triple_team_count)
      * ln(1 + triple_lift)
      * ln(1 + avg_pair_lift) as candidate_score_raw
  from {{ ref('pokemon_team_core_triple_usage') }}
  where triple_team_count >= 5
    and triple_lift > 1
    and avg_pair_lift > 1
),
neighbours as (
  select
    candidate.candidate_key,
    anchor.candidate_key as anchor_candidate_key,
    anchor.pokemon_key_a as anchor_pokemon_key_a,
    anchor.pokemon_key_b as anchor_pokemon_key_b,
    anchor.pokemon_key_c as anchor_pokemon_key_c,
    row_number() over (
      partition by candidate.candidate_key
      order by anchor.candidate_score_raw desc,
        anchor.triple_team_count desc,
        anchor.candidate_key
    ) as anchor_rank
  from eligible candidate
  inner join eligible anchor
    on (
      case when candidate.pokemon_key_a in (
        anchor.pokemon_key_a, anchor.pokemon_key_b, anchor.pokemon_key_c
      ) then 1 else 0 end
      + case when candidate.pokemon_key_b in (
        anchor.pokemon_key_a, anchor.pokemon_key_b, anchor.pokemon_key_c
      ) then 1 else 0 end
      + case when candidate.pokemon_key_c in (
        anchor.pokemon_key_a, anchor.pokemon_key_b, anchor.pokemon_key_c
      ) then 1 else 0 end
    ) >= 2
)
select
  eligible.candidate_key,
  'detected-' || neighbours.anchor_candidate_key as archetype_key,
  eligible.pokemon_key_a,
  eligible.pokemon_key_b,
  eligible.pokemon_key_c,
  neighbours.anchor_candidate_key,
  neighbours.anchor_pokemon_key_a,
  neighbours.anchor_pokemon_key_b,
  neighbours.anchor_pokemon_key_c,
  eligible.triple_team_count,
  eligible.player_count,
  eligible.event_count,
  eligible.triple_team_share,
  eligible.triple_lift,
  eligible.min_pair_lift,
  eligible.avg_pair_lift,
  round(eligible.candidate_score_raw, 4) as candidate_score
from eligible
inner join neighbours
  on neighbours.candidate_key = eligible.candidate_key
  and neighbours.anchor_rank = 1
order by candidate_score desc, candidate_key
