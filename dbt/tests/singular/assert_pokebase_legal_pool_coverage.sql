-- Gate: >=95% of PokéBase legal-pool rows mapped to canonical pokemon_id (docs/dataset-spec.md).
-- With zero staged rows this is vacuously not failed (pending PokéBase extraction).
-- Measures real mapped coverage (rows int_pokebase_mapped resolved to a pokemon_key,
-- via the pokebase_slug_to_pokeapi_form seed).
-- fail_calc must resolve to an integer (dbt's run-results schema requires it), so this
-- reports coverage in basis points (100% = 10000 bps); pipelines/validate/report.py
-- divides by 10000 to recover the ratio for the report's metric_value.
{{ config(fail_calc='max(coverage_bps)', error_if='<9500', warn_if='<9500') }}
select
  case
    when total.row_count = 0 then 10000
    else round(mapped.mapped_count::double / total.row_count * 10000)::integer
  end as coverage_bps
from (
  select count(*) as row_count
  from {{ source('staging', 'pokebase') }}
) total
cross join (
  select count(*) as mapped_count
  from {{ ref('int_pokebase_mapped') }}
) mapped
