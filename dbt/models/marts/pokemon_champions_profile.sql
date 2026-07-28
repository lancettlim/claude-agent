{{ config(location='../data/marts/pokemon_champions_profile.csv') }}
-- Denormalized per-Pokémon profile for the dashboard's Speed Tiers, Team
-- Builder, Pokémon Profile, and Matchup views (docs/todo.md M6 backlog):
-- one row per currently legal Pokémon, combining its Champions-format base
-- stats (speed, for speed-tier ordering), its type_1/type_2 (for the
-- Profile type badge, type/role filters, and the Matchup tab's type
-- effectiveness and damage calculator), and its overall usage/win-rate
-- KPIs, so those views can list/sort/filter the legal pool without joining
-- multiple marts client-side. usage_count/usage_share/win_rate/
-- record_count are nullable — real MunchStats tournament data doesn't
-- cover every legal Pokémon, and a null here means "not yet seen in a
-- recorded roster", not zero.
select
  champions.pokemon_key,
  pokemon.type_1,
  pokemon.type_2,
  champions.hp,
  champions.attack,
  champions.defense,
  champions.sp_attack,
  champions.sp_defense,
  champions.speed,
  champions.stat_total,
  usage.usage_count,
  usage.usage_share,
  win.win_rate,
  win.record_count
from {{ ref('pokemon_stat_champions') }} champions
left join {{ ref('pokemon') }} pokemon
  on pokemon.pokemon_key = champions.pokemon_key
left join (
  select * from {{ ref('pokemon_usage_summary') }} where event_tier is null
) usage
  on usage.pokemon_key = champions.pokemon_key
left join {{ ref('pokemon_win_rate_summary') }} win
  on win.pokemon_key = champions.pokemon_key
where champions.is_legal = true
order by champions.speed desc
