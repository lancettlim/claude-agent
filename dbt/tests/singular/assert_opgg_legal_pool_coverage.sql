-- Gate: >=95% of OP.GG legal pool mapped to canonical pokemon_id (docs/dataset-spec.md).
-- Zero staged rows reports 0 coverage (fails the gate) rather than passing
-- vacuously: the source's external_location glob (_sources.yml) errors out
-- before this query ever runs if no snapshot file exists at all, so a
-- zero-row result here only happens when a snapshot file exists but is
-- empty -- exactly the total-upstream-outage case this gate exists to catch
-- (docs/backlog.md #36).
-- Measures real mapped coverage (rows int_opgg_champions_mapped resolved to a
-- pokemon_key, via direct id or the opgg_key_to_pokeapi_form seed fallback), not
-- just staging's raw pokemon_id nullness — the seed fallback maps many
-- fabricated-id rows that raw pokemon_id alone would miss.
-- fail_calc must resolve to an integer (dbt's run-results schema requires it), so this
-- reports coverage in basis points (100% = 10000 bps); pipelines/validate/report.py
-- divides by 10000 to recover the ratio for the report's metric_value.
{{ config(fail_calc='max(coverage_bps)', error_if='<9500', warn_if='<9500', meta={'category': 'coverage', 'check_name': 'opgg_legal_pool_coverage', 'description': 'Share of OP.GG legal pool rows mapped to a canonical pokemon_id', 'threshold': '>=0.95'}) }}
select
  case
    when total.legal_count = 0 then 0
    else round(mapped.mapped_count::double / total.legal_count * 10000)::integer
  end as coverage_bps
from (
  select count(*) as legal_count
  from {{ source('staging', 'opgg_champions') }}
  where is_legal = true
) total
cross join (
  select count(*) as mapped_count
  from {{ ref('int_opgg_champions_mapped') }}
  where is_legal = true
) mapped
