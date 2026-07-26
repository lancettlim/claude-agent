{{ config(location='../data/marts/legality_summary_by_regulation.csv') }}
-- KPI card feed (docs/prd.md's "KPI overview cards ... legality changes";
-- docs/todo.md's "Document KPI views and filter dimensions (regulation/
-- date/...)"): current legal-pool size per regulation and snapshot date,
-- both independent (legal_pokemon_count: this regulation only) and
-- cumulative (cumulative_legal_pokemon_count: a naive union of every
-- regulation_code that sorts lexicographically <= this one, within the
-- same snapshot_date). Regulation codes ("m-a", "m-b", ...) are assumed to
-- sort lexicographically in the same order Champions itself releases them
-- in -- true of every code observed so far, but nothing in the source data
-- structurally guarantees it, so this is stated here rather than left
-- implicit.
--
-- CAVEAT (docs/dashboard.md, this model's schema.yml entry): PokéBase, the
-- sole source of legality_snapshot, only ever publishes positive ("this
-- Pokémon is legal") signals -- a Pokémon's absence from a later
-- regulation's snapshot isn't distinguishable from "not yet observed" vs.
-- "actually banned". cumulative_legal_pokemon_count can therefore only grow
-- across regulations; it will silently keep counting a Pokémon that was
-- really removed in a later regulation, since no removal event exists to
-- subtract it back out.
with legal_rows as (
  select regulation_code, snapshot_date, pokemon_key
  from {{ ref('legality_snapshot') }}
  where is_legal = true
),
regulations as (
  select distinct regulation_code, snapshot_date from legal_rows
),
independent_counts as (
  select regulation_code, snapshot_date, count(*) as legal_pokemon_count
  from legal_rows
  group by regulation_code, snapshot_date
),
cumulative_counts as (
  select
    r.regulation_code,
    r.snapshot_date,
    count(distinct l.pokemon_key) as cumulative_legal_pokemon_count
  from regulations r
  inner join legal_rows l
    on l.snapshot_date = r.snapshot_date
    and l.regulation_code <= r.regulation_code
  group by r.regulation_code, r.snapshot_date
)
select
  i.regulation_code,
  i.snapshot_date,
  i.legal_pokemon_count,
  c.cumulative_legal_pokemon_count
from independent_counts i
inner join cumulative_counts c
  on c.regulation_code = i.regulation_code
  and c.snapshot_date = i.snapshot_date
order by regulation_code
