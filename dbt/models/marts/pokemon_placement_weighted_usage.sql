{{ config(location='../data/marts/pokemon_placement_weighted_usage.csv') }}
-- Placement-weighted usage (backlog.md #8): distinguishes "popular" from
-- "successful" -- raw pokemon_usage_summary.usage_count treats a
-- last-place team's roster slot the same as a tournament winner's, which
-- flatters crowd-favorite picks and hides quiet top-cut staples.
--
-- Two views, both derived from tournament_team.placement (always reported,
-- lower is better -- 1 is first place):
--   - top_cut_usage_count/top_cut_usage_share: appearances on a team that
--     placed 1-8 ("top cut", the standard VGC/Champions cutoff for a
--     tournament's single-elimination bracket) -- a hard cutoff view.
--   - placement_weighted_score/weighted_usage_share: a continuously
--     weighted view using an inverse-placement weight (1/placement) per
--     appearance, so a 1st-place finish counts far more than a 200th, with
--     no cutoff discontinuity.
with legal_appearances as (
  select member.pokemon_key, team.placement
  from {{ ref('tournament_team_member') }} member
  inner join {{ ref('tournament_team') }} team
    on team.team_id = member.team_id
  inner join {{ ref('pokemon_stat_champions') }} champions
    on champions.pokemon_key = member.pokemon_key
    and champions.is_legal = true
  where team.placement is not null
    and team.placement > 0
),
per_pokemon as (
  select
    pokemon_key,
    count(*) as usage_count,
    sum(case when placement <= 8 then 1 else 0 end) as top_cut_usage_count,
    sum(1.0 / placement) as placement_weighted_score
  from legal_appearances
  group by pokemon_key
)
select
  pokemon_key,
  usage_count,
  top_cut_usage_count,
  round(
    top_cut_usage_count::double / nullif(sum(top_cut_usage_count) over (), 0),
    4
  ) as top_cut_usage_share,
  round(placement_weighted_score, 4) as placement_weighted_score,
  round(
    placement_weighted_score / nullif(sum(placement_weighted_score) over (), 0),
    4
  ) as weighted_usage_share,
  row_number() over (order by placement_weighted_score desc) as weighted_usage_rank
from per_pokemon
order by placement_weighted_score desc
