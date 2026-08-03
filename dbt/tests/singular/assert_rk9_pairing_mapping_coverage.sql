-- Gate: >=90% of RK9 Masters pairing player slots resolve to a
-- tournament_team row (docs/dataset-spec.md), matching the threshold the
-- equivalent MunchStats roster-mapping gate already uses.
--
-- Scoped to the Masters division deliberately. MunchStats scrapes Masters
-- rosters only, so Junior and Senior pairings have no team to resolve to by
-- construction -- including them would measure MunchStats' division scope
-- rather than this mapping's health, and would sit permanently below any
-- useful threshold. Byes are excluded on the opponent side for the same
-- reason: a bye has no second player to map.
--
-- Real measured coverage: 1003/1007 = 99.6% of NAIC 2026 round-5 Masters
-- slots. The residual is players who appear in pairings but never submitted
-- a team list (dropped early), which is a real property of the data rather
-- than a mapping defect.
--
-- Zero staged rows reports 0 coverage (fails the gate) rather than passing
-- vacuously -- see assert_bulbagarden_sprite_coverage.sql's header and
-- docs/backlog.md #36 for why that branch matters.
-- fail_calc must resolve to an integer (dbt's run-results schema requires it), so this
-- reports coverage in basis points (100% = 10000 bps); pipelines/validate/report.py
-- divides by 10000 to recover the ratio for the report's metric_value.
{{ config(fail_calc='max(coverage_bps)', error_if='<9000', warn_if='<9000', meta={'category': 'coverage', 'check_name': 'rk9_pairing_mapping_coverage', 'description': 'Share of RK9 Masters pairing player slots resolved to a tournament_team row', 'threshold': '>=0.90'}) }}
with slots as (
  select team_id_1 as team_id
  from {{ ref('tournament_match') }}
  where division = 'Masters'
  union all
  select team_id_2 as team_id
  from {{ ref('tournament_match') }}
  where division = 'Masters'
    and outcome <> 'bye'
)

select
  case
    when count(*) = 0 then 0
    else round(
      sum(case when team_id is not null then 1 else 0 end)::double / count(*) * 10000
    )::integer
  end as coverage_bps
from slots
