{{ config(location='../data/marts/pokemon_stat_profile.csv') }}
-- Stat/type/image profile per legal Pokémon (VGC player-focused dashboard
-- pass: powers the speed-tier list, the stat-comparison view, and
-- image/type display everywhere else in the dashboards). Joins
-- pokemon_stat_champions (restricted to the current legal pool, the same
-- convention every other mart uses for "the" base stats) with pokemon's
-- type/image attributes.
select
  champions.pokemon_key,
  champions.hp,
  champions.attack,
  champions.defense,
  champions.sp_attack,
  champions.sp_defense,
  champions.speed,
  champions.stat_total,
  poke.type_1,
  poke.type_2,
  poke.image_url
from {{ ref('pokemon_stat_champions') }} champions
inner join {{ ref('pokemon') }} poke
  on poke.pokemon_key = champions.pokemon_key
where champions.is_legal = true
order by champions.speed desc
