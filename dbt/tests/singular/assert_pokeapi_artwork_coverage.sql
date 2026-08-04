-- Gate: >=95% of forms with a Champions menu sprite also have a
-- high-resolution home_render row (docs/dataset-spec.md).
--
-- Denominator is menu_sprite rows rather than the Champions legal pool
-- because that is exactly the set the extractor is scoped to: pipelines/
-- cli.py's _champions_form_resource_ids() reads the
-- bulbagarden_title_to_pokeapi_form seed, so this gate measures the thing
-- that can actually go wrong -- artwork silently failing to download, or
-- upstream 404ing on a form -- rather than re-measuring Bulbagarden's own
-- coverage, which assert_bulbagarden_sprite_coverage.sql already gates.
--
-- The threshold is 95%, not Bulbagarden's 85%, because none of what
-- justifies the lower floor there applies here: that gate's denominator is
-- raw file titles, several of which collapse onto one pokemon_key by
-- design (Vivillon patterns, Florges colors, Furfrou trims, Alcremie
-- flavors). Both sides of this ratio are already per-pokemon_key, so a
-- shortfall here is a real missing render, not a dedup artifact.
--
-- Zero menu_sprite rows reports 0 coverage (fails) rather than passing
-- vacuously, matching assert_bulbagarden_sprite_coverage.sql's handling of
-- the total-upstream-outage case (docs/backlog.md #36).
--
-- fail_calc must resolve to an integer (dbt's run-results schema requires it), so this
-- reports coverage in basis points (100% = 10000 bps); pipelines/validate/report.py
-- divides by 10000 to recover the ratio for the report's metric_value.
{{ config(fail_calc='max(coverage_bps)', error_if='<9500', warn_if='<9500', meta={'category': 'coverage', 'check_name': 'pokeapi_artwork_coverage', 'description': 'Share of menu-sprite Pokémon that also have a high-resolution home_render asset', 'threshold': '>=0.95'}) }}
select
  case
    when sprite.sprite_count = 0 then 0
    else round(render.render_count::double / sprite.sprite_count * 10000)::integer
  end as coverage_bps
from (
  select count(*) as sprite_count
  from {{ ref('pokemon_asset') }}
  where image_kind = 'menu_sprite'
) sprite
cross join (
  select count(*) as render_count
  from {{ ref('pokemon_asset') }}
  where image_kind = 'home_render'
) render
