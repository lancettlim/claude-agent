{{ config(location='../data/marts/archetype_summary.csv') }}
-- Archetype Explorer card-grid feed: one row per curated archetype,
-- rolling up pokemon_archetype_usage's member-level rows into a
-- combined_usage_share (sum of members' usage_share -- a rough proxy for
-- how much of the meta this archetype's core pieces occupy, not a
-- probability that all members appear on the same team) and an
-- avg_win_rate across members with recorded win-rate data.
-- top_member_pokemon_key is whichever member ranks #1 by usage_share
-- within the archetype (pokemon_archetype_usage.member_rank = 1); the
-- dashboard build resolves it to a display name/sprite the same way it
-- already resolves every other pokemon_key.
select
  archetype_key,
  archetype_name,
  count(*) as member_count,
  round(sum(usage_share), 4) as combined_usage_share,
  round(avg(win_rate), 4) as avg_win_rate,
  max(case when member_rank = 1 then pokemon_key end) as top_member_pokemon_key
from {{ ref('pokemon_archetype_usage') }}
group by archetype_key, archetype_name
order by combined_usage_share desc nulls last
