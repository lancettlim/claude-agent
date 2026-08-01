{{ config(location='../data/marts/pokemon_usage_by_regulation.csv') }}
-- Usage x regulation cross-tab (backlog.md #12: usage is currently sliced
-- by event_tier but never scoped to a regulation, so a single usage_count
-- silently mixes Pokémon that are legal under different regulation
-- codes' legal pools). tournament_event carries no regulation_code of its
-- own (MunchStats doesn't report which regulation an event was played
-- under), so this isn't a "usage during regulation X" temporal slice --
-- it's pokemon_usage_summary's overall usage_count cross-joined against
-- legality_snapshot's regulation membership at the latest snapshot_date,
-- letting the dashboard filter/rank the existing usage numbers down to
-- "Pokémon legal under regulation X" instead of the whole legal pool.
--
-- usage_share/usage_rank are recomputed within each regulation_code
-- partition (mirroring pokemon_usage_summary's event_tier partitioning),
-- so a Pokémon's share reflects its standing among that regulation's own
-- legal pool, not the union across regulations.
with overall_usage as (
  select pokemon_key, usage_count
  from {{ ref('pokemon_usage_summary') }}
  where event_tier is null
),
latest_snapshot as (
  select max(snapshot_date) as snapshot_date
  from {{ ref('legality_snapshot') }}
),
legal_by_regulation as (
  select ls.regulation_code, ls.pokemon_key
  from {{ ref('legality_snapshot') }} ls
  inner join latest_snapshot
    on latest_snapshot.snapshot_date = ls.snapshot_date
  where ls.is_legal = true
),
joined as (
  select
    legal_by_regulation.regulation_code,
    legal_by_regulation.pokemon_key,
    coalesce(overall_usage.usage_count, 0) as usage_count
  from legal_by_regulation
  left join overall_usage
    on overall_usage.pokemon_key = legal_by_regulation.pokemon_key
)
select
  regulation_code,
  pokemon_key,
  usage_count,
  round(
    usage_count::double / nullif(sum(usage_count) over (partition by regulation_code), 0),
    4
  ) as usage_share,
  row_number() over (partition by regulation_code order by usage_count desc) as usage_rank
from joined
order by regulation_code, usage_count desc
