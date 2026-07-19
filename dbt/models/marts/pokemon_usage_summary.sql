{{ config(location='../data/marts/pokemon_usage_summary.csv') }}
-- Flat analytical export (docs/todo.md's Phase 3 "Publish flat analytical
-- exports and summary aggregates" item): total tournament-roster usage per
-- Pokémon, restricted to the current legal pool, ranked descending.
--
-- event_tier is an optional filter dimension (docs/todo.md's "tournament-
-- tier filtering" follow-up): every Pokémon gets one overall row
-- (event_tier is null) plus one row per tournament tier it appears in,
-- each ranked within its own event_tier partition — so the overall
-- ranking is unaffected by adding the per-tier breakdown.
with overall as (
  select
    member.pokemon_key,
    cast(null as varchar) as event_tier,
    count(*) as usage_count
  from {{ ref('tournament_team_member') }} member
  inner join {{ ref('pokemon_stat_champions') }} champions
    on champions.pokemon_key = member.pokemon_key
    and champions.is_legal = true
  group by member.pokemon_key
),
by_tier as (
  select
    member.pokemon_key,
    event.event_tier,
    count(*) as usage_count
  from {{ ref('tournament_team_member') }} member
  inner join {{ ref('pokemon_stat_champions') }} champions
    on champions.pokemon_key = member.pokemon_key
    and champions.is_legal = true
  inner join {{ ref('tournament_event') }} event
    on event.event_id = member.event_id
  where event.event_tier is not null
  group by member.pokemon_key, event.event_tier
)
select
  pokemon_key,
  event_tier,
  usage_count,
  row_number() over (partition by event_tier order by usage_count desc) as usage_rank
from (
  select * from overall
  union all
  select * from by_tier
)
