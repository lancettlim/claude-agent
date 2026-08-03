-- One row per Pokémon on a canonical Limitless team list, with the build
-- details the published team sheet carries: held item, ability, nature and
-- moveset.
--
-- Note what is absent and why: no EV or IV spread. Official tournament team
-- sheets (RK9's own, which Limitless republishes) report ability, held
-- item, "Stat Alignment" (nature) and moves, and nothing more -- EVs are
-- not published by the tournament apparatus at all. See
-- docs/data-sources.md's Victory Road entry for the measurement behind
-- that, and backlog.md #25.
--
-- Grain is the team composition, not the player. Several players across
-- several events can share one team_list_id, and the build is identical
-- across them by construction (it is the same published list), so this
-- groups rather than selecting distinct: the per-player source_record_id
-- differs between those rows even though everything describing the team
-- does not, and a plain distinct would emit one row per player and break
-- the primary key.
select
  limitless_team_id || ':' || cast(slot_number as varchar) as team_list_member_id,
  limitless_team_id as team_list_id,
  max(pokemon_key) as pokemon_key,
  max(pokemon_id) as pokemon_id,
  slot_number,
  max(item_name) as item_name,
  max(ability) as ability,
  max(nature) as nature,
  max(moves) as moves,
  max(source_name) as source_name,
  max(source_url) as source_url,
  min(source_record_id) as source_record_id,
  max(extracted_at_utc) as extracted_at_utc,
  max(dataset_version) as dataset_version
from {{ ref('int_limitless_mapped') }}
group by limitless_team_id, slot_number
