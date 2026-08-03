{{ config(location='../data/marts/pokemon_team_synergy.csv') }}
-- Team synergy beyond raw co-occurrence (backlog.md #9): pokemon_team_
-- core_usage reports how often two Pokémon appear together, which mostly
-- just re-ranks the individually popular ones. This mart adds lift -- the
-- ratio of a pair's observed team co-occurrence rate to the co-occurrence
-- rate you'd expect if the two Pokémon were paired independently of their
-- individual popularity:
--
--   lift(A, B) = P(A and B) / (P(A) * P(B))
--              = (pair_team_count / total_teams)
--                / ((team_count_a / total_teams) * (team_count_b / total_teams))
--
-- lift > 1 means the pair appears together more than chance given how
-- popular each Pokémon is individually -- a genuine pairing, not just two
-- popular Pokémon coincidentally sharing rosters. lift < 1 means they're
-- paired together less than their individual popularity would predict.
--
-- Built on top of pokemon_team_core_usage's already-mirrored pairs (both
-- anchor directions) rather than re-deriving the pairwise team self-join,
-- plus a small marginal (how many distinct teams include this Pokémon at
-- all) and total-team-count aggregate.
--
-- CAVEAT: lift is noisy for low pair_team_count (a pair seen together
-- twice against a Pokémon that's individually rare can produce an
-- extreme lift value) -- pair_team_count is exposed alongside lift so
-- consumers can apply their own confidence floor, the same pattern
-- pokemon_win_rate_summary's record_count/wilson_lower_bound pairing
-- uses.
with legal_members as (
  select distinct member.team_id, member.pokemon_key
  from {{ ref('int_champions_roster') }} member
  inner join {{ ref('pokemon_stat_champions') }} champions
    on champions.pokemon_key = member.pokemon_key
    and champions.is_legal = true
),
total_teams as (
  select count(distinct team_id) as total_teams from legal_members
),
marginal as (
  select pokemon_key, count(distinct team_id) as team_count
  from legal_members
  group by pokemon_key
),
scored as (
  select
    core.pokemon_key,
    core.partner_pokemon_key,
    core.co_occurrence_count as pair_team_count,
    (core.co_occurrence_count::double * total_teams.total_teams)
      / (marginal_a.team_count * marginal_b.team_count) as lift_raw
  from {{ ref('pokemon_team_core_usage') }} core
  cross join total_teams
  inner join marginal marginal_a on marginal_a.pokemon_key = core.pokemon_key
  inner join marginal marginal_b on marginal_b.pokemon_key = core.partner_pokemon_key
)
select
  pokemon_key,
  partner_pokemon_key,
  pair_team_count,
  round(lift_raw, 4) as lift,
  row_number() over (partition by pokemon_key order by lift_raw desc) as lift_rank
from scored
order by pokemon_key, lift desc
