{{ config(location='../data/marts/pokemon_usage_by_country.csv') }}
-- Country-grain half of backlog.md #7 ("which regions favor which
-- archetypes"): usage x player_country cross-tab, mirroring
-- pokemon_usage_by_regulation's usage-x-dimension pattern (backlog.md
-- #12) rather than pokemon_usage_summary's event_tier rows-plus-overall
-- shape, since there's no meaningful "overall" row here beyond what
-- pokemon_usage_summary already reports.
--
-- usage_share is usage_count's fraction of total roster appearances within
-- the same player_country partition -- "what does this region actually
-- play," not a raw count dominated by whichever country fielded the most
-- teams. Restricted to the current legal pool and to roster rows with a
-- reported player_country (tournament_team.player_country is optional --
-- not every MunchStats player row reports it).
select
  member.pokemon_key,
  team.player_country,
  count(*) as usage_count,
  round(
    count(*)::double / sum(count(*)) over (partition by team.player_country),
    4
  ) as usage_share,
  row_number() over (
    partition by team.player_country order by count(*) desc
  ) as country_usage_rank
from {{ ref('int_champions_roster') }} member
inner join {{ ref('pokemon_stat_champions') }} champions
  on champions.pokemon_key = member.pokemon_key
  and champions.is_legal = true
inner join {{ ref('tournament_team') }} team
  on team.team_id = member.team_id
where team.player_country is not null and team.player_country != ''
group by member.pokemon_key, team.player_country
