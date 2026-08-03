-- Gate: a tournament_match team reference, where present, must resolve to a
-- real tournament_team row (docs/dataset-spec.md).
--
-- A null team_id is not a violation and is excluded: a bye has no opponent,
-- and Junior/Senior division players have no MunchStats roster to resolve
-- against at all. How *many* references stay unresolved is the separate
-- concern of assert_rk9_pairing_mapping_coverage.sql; this gate only asserts
-- that a reference which does exist points at something real.
{{ config(meta={'category': 'referential_integrity', 'check_name': 'tournament_match_resolves_to_tournament_team'}) }}
select child.match_id, child.team_id
from (
  select match_id, team_id_1 as team_id from {{ ref('tournament_match') }}
  union all
  select match_id, team_id_2 as team_id from {{ ref('tournament_match') }}
) child
left join {{ ref('tournament_team') }} parent on child.team_id = parent.team_id
where child.team_id is not null
  and parent.team_id is null
