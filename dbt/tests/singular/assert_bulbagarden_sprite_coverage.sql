-- Gate: >=85% of Bulbagarden sprite titles mapped to pokemon_asset rows (docs/dataset-spec.md).
-- With zero staged rows this is vacuously not failed (pending Bulbagarden extraction).
-- Threshold is lower than OP.GG's 95%/MunchStats's 90% because pokemon_asset's
-- primary key is pokemon_key, not bulbagarden_title: several species (Vivillon's
-- wing patterns, Florges's colors, Furfrou's trims, Alcremie's cream flavors,
-- Pyroar's cosmetic female sprite) have many Bulbagarden titles collapsing onto
-- one pokemon_key by design (see int_bulbagarden_mapped.sql's dedup step and
-- dbt/seeds/schema.yml's bulbagarden_title_to_pokeapi_form notes), which lowers
-- this row-count ratio without indicating a real mapping gap. Real measured
-- coverage at seed-build time was 317/359 titles (88.3%); one title (Mega
-- Meowstic) was deliberately left unmapped rather than guessed.
-- fail_calc must resolve to an integer (dbt's run-results schema requires it), so this
-- reports coverage in basis points (100% = 10000 bps); pipelines/validate/report.py
-- divides by 10000 to recover the ratio for the report's metric_value.
{{ config(fail_calc='max(coverage_bps)', error_if='<8500', warn_if='<8500') }}
select
  case
    when total.title_count = 0 then 10000
    else round(mapped.asset_count::double / total.title_count * 10000)::integer
  end as coverage_bps
from (
  select count(*) as title_count
  from {{ source('staging', 'bulbagarden') }}
) total
cross join (
  select count(*) as asset_count
  from {{ ref('pokemon_asset') }}
) mapped
