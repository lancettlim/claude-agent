-- Held-item reference detail (short_effect), scoped to items reported in
-- real tournament roster data. See docs/dataset-spec.md's "item_detail"
-- entity definition. Dashboard-support reference data, not a release-gated
-- core entity -- see dataset-spec.md for the explicit scope note.
select
  item_name,
  short_effect,
  source_name,
  source_url,
  source_record_id,
  extracted_at_utc,
  dataset_version
from {{ ref('int_pokeapi_item_latest') }}
