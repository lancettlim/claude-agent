-- Derived canonical-vs-Champions stat change output, joining
-- pokemon_stat_canonical and pokemon_stat_champions on pokemon_key. Only
-- covers pokemon_key values present in both (i.e. Champions-legal forms
-- that were successfully mapped to a canonical PokéAPI row).
select
  canonical.pokemon_key || '-delta' as pokemon_stat_delta_key,
  canonical.pokemon_key,
  canonical.pokemon_id,
  champions.hp - canonical.hp as hp_delta,
  champions.attack - canonical.attack as attack_delta,
  champions.defense - canonical.defense as defense_delta,
  champions.sp_attack - canonical.sp_attack as sp_attack_delta,
  champions.sp_defense - canonical.sp_defense as sp_defense_delta,
  champions.speed - canonical.speed as speed_delta,
  champions.stat_total - canonical.stat_total as stat_total_delta,
  canonical.dataset_version as canonical_dataset_version,
  champions.dataset_version as champions_dataset_version,
  'derived: pokemon_stat_canonical vs pokemon_stat_champions' as source_name,
  'internal://pokemon_stat_delta' as source_url,
  champions.extracted_at_utc,
  champions.dataset_version
from {{ ref('pokemon_stat_canonical') }} canonical
inner join {{ ref('pokemon_stat_champions') }} champions
  on canonical.pokemon_key = champions.pokemon_key
