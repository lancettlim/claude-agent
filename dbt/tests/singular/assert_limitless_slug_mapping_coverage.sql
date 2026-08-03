-- Gate: >=85% of staged Limitless roster slots resolve to a pokemon_key
-- (docs/dataset-spec.md), matching the Bulbagarden threshold -- this is the
-- same class of problem (a source's own form-naming convention reconciled
-- through a controlled seed), so it gets the same bar rather than a new one.
--
-- Real measured coverage at seed-build time was 83/83 distinct slugs, i.e.
-- 100% of rows: 78 slugs match a PokéAPI form_name outright and the other
-- five resolve through the seed. The threshold is set below that on
-- purpose, to catch a genuine upstream renaming rather than to freeze
-- today's number.
--
-- Zero staged rows reports 0 coverage (fails the gate) rather than passing
-- vacuously -- see assert_bulbagarden_sprite_coverage.sql's header and
-- docs/backlog.md #36 for why that branch matters.
-- fail_calc must resolve to an integer (dbt's run-results schema requires it), so this
-- reports coverage in basis points (100% = 10000 bps); pipelines/validate/report.py
-- divides by 10000 to recover the ratio for the report's metric_value.
{{ config(fail_calc='max(coverage_bps)', error_if='<8500', warn_if='<8500', meta={'category': 'coverage', 'check_name': 'limitless_slug_mapping_coverage', 'description': 'Share of staged Limitless roster slots resolved to a canonical pokemon_key', 'threshold': '>=0.85'}) }}
select
  case
    when total.slot_count = 0 then 0
    else round(mapped.slot_count::double / total.slot_count * 10000)::integer
  end as coverage_bps
from (
  select count(*) as slot_count
  from {{ ref('int_limitless_latest') }}
) total
cross join (
  select count(*) as slot_count
  from {{ ref('int_limitless_mapped') }}
) mapped
