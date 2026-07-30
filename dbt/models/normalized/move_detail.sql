-- Move reference detail (type/power/accuracy/category/priority/pp/
-- short_effect), scoped to moves reported in real tournament roster data.
-- See docs/dataset-spec.md's "move_detail" entity definition. Dashboard-
-- support reference data (Pokémon Profile move descriptions, Matchup tab
-- damage calculator) rather than a per-record fact about a Pokémon or
-- tournament, so it isn't a release-gated core entity -- see
-- dataset-spec.md for the explicit scope note.
select
  move_name,
  move_type,
  power,
  accuracy,
  category,
  priority,
  pp,
  short_effect,
  source_name,
  source_url,
  source_record_id,
  extracted_at_utc,
  dataset_version
from {{ ref('int_pokeapi_move_latest') }}
