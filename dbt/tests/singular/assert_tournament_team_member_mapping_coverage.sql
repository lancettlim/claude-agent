-- Gate: >=90% of tournament records mapped to normalized team tables (docs/dataset-spec.md).
-- Zero staged rows reports 0 coverage (fails the gate) rather than passing
-- vacuously: the source's external_location glob (_sources.yml) errors out
-- before this query ever runs if no snapshot file exists at all, so a
-- zero-row result here only happens when a snapshot file exists but is
-- empty -- exactly the total-upstream-outage case this gate exists to catch
-- (docs/backlog.md #36).
-- fail_calc must resolve to an integer (dbt's run-results schema requires it), so this
-- reports coverage in basis points (100% = 10000 bps); pipelines/validate/report.py
-- divides by 10000 to recover the ratio for the report's metric_value.
{{ config(fail_calc='max(coverage_bps)', error_if='<9000', warn_if='<9000') }}
select
  case
    when count(*) = 0 then 0
    else round((
      select count(*) from {{ ref('tournament_team_member') }}
    )::double / count(*) * 10000)::integer
  end as coverage_bps
from {{ source('staging', 'munchstats') }}
