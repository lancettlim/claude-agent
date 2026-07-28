{{ config(location='../data/marts/pokemon_team_core_usage.csv') }}
-- Team-core drill-down (docs/prd.md's "Drill-down by Pokémon, team core,
-- move, and item usage" — named in scope but never built until now):
-- co-occurrence usage count per Pokémon x partner Pokémon pair appearing
-- on the same tournament team, restricted to the current legal pool.
--
-- partner_share is co_occurrence_count's fraction of that Pokémon's own
-- total co-occurrence count across all partners (dashboard "percentages,
-- not raw counts" ask), the same share-of-own-total pattern
-- pokemon_usage_summary.usage_share/pokemon_item_usage.item_share/
-- pokemon_move_usage.move_share use.
with legal_members as (
  select member.team_member_id, member.team_id, member.pokemon_key
  from {{ ref('tournament_team_member') }} member
  inner join {{ ref('pokemon_stat_champions') }} champions
    on champions.pokemon_key = member.pokemon_key
    and champions.is_legal = true
),
pairs as (
  -- a.pokemon_key < b.pokemon_key both excludes self-pairs and dedupes
  -- each unordered pair to a single canonical ordering, mirroring how
  -- the other marts key off pokemon_key.
  select a.pokemon_key as pokemon_key_a, b.pokemon_key as pokemon_key_b
  from legal_members a
  inner join legal_members b
    on a.team_id = b.team_id
    and a.pokemon_key < b.pokemon_key
),
counted as (
  select pokemon_key_a, pokemon_key_b, count(*) as co_occurrence_count
  from pairs
  group by pokemon_key_a, pokemon_key_b
),
-- Mirror each pair into both anchor directions so the dashboard can look
-- up "who pairs with X" for either member of the pair.
mirrored as (
  select pokemon_key_a as pokemon_key, pokemon_key_b as partner_pokemon_key,
    co_occurrence_count
  from counted
  union all
  select pokemon_key_b as pokemon_key, pokemon_key_a as partner_pokemon_key,
    co_occurrence_count
  from counted
)
select
  pokemon_key,
  partner_pokemon_key,
  co_occurrence_count,
  round(
    co_occurrence_count::double
      / sum(co_occurrence_count) over (partition by pokemon_key),
    4
  ) as partner_share,
  row_number() over (
    partition by pokemon_key
    order by co_occurrence_count desc
  ) as usage_rank
from mirrored
order by pokemon_key, co_occurrence_count desc
