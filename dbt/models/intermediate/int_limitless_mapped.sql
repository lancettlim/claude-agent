-- Resolves Limitless' own species slugs to canonical pokemon_key via the
-- limitless_slug_to_pokeapi_form seed, mirroring how the OP.GG, MunchStats,
-- PokéBase and Bulbagarden mapped models each resolve their source's
-- naming convention.
--
-- Limitless slugs follow PokéAPI's own form-naming convention closely: 78
-- of the 83 slugs seen in real Champions team lists match a pokeapi
-- form_name outright. The five that don't (aegislash, basculegion,
-- maushold, mimikyu, palafin) are species whose PokéAPI entry has no bare
-- form, only explicit ones; the seed resolves each to the same default
-- battle form dbt/seeds/munchstats_name_to_pokeapi_form.csv already picks
-- for the identical case, rather than inventing a second convention.
--
-- Mega forms need a second resolution step, and finding out why is exactly
-- what ingesting a second source bought: Limitless and MunchStats describe
-- the same team differently. Limitless publishes the *base* species holding
-- its Mega Stone ("Charizard" + "Charizardite Y"), while MunchStats
-- publishes the already-evolved form ("Charizard-Mega-Y"). Both are correct
-- readings of the same team sheet, but taken literally the Limitless row
-- would join to base-Charizard's stats, which are not the stats that
-- Pokémon actually played with -- so this is a correctness fix, not just a
-- comparison convenience. limitless_mega_item_to_pokeapi_form resolves
-- (slug, Mega Stone) to the evolved form; a Pokémon holding anything else
-- keeps its base form, and Charizard's two megas are told apart by the
-- stone's own X/Y suffix. Discovered via roster_source_agreement.sql, which
-- reported 0% exact agreement until this was applied.
--
-- An unmapped slug is dropped, matching tournament_team_member.sql: per
-- docs/dataset-spec.md, unmapped rows must not ship in release outputs.
select
  source.limitless_team_id,
  source.tournament_id,
  source.rk9_event_id,
  source.tournament_name,
  source.tournament_date,
  source.regulation_set,
  source.placement,
  source.player_name,
  source.player_country,
  source.limitless_player_id,
  source.slot_number,
  source.pokemon_slug,
  pokemon.pokemon_key,
  pokemon.pokemon_id,
  source.item_name,
  source.ability,
  source.nature,
  source.moves,
  source.source_name,
  source.source_url,
  source.source_record_id,
  source.extracted_at_utc,
  source.dataset_version
from {{ ref('int_limitless_latest') }} source
inner join {{ ref('limitless_slug_to_pokeapi_form') }} seed_map
  on seed_map.limitless_pokemon_slug = source.pokemon_slug
left join {{ ref('limitless_mega_item_to_pokeapi_form') }} mega_map
  on mega_map.limitless_pokemon_slug = source.pokemon_slug
  and mega_map.item_name = source.item_name
inner join {{ ref('pokemon') }} pokemon
  on pokemon.form_name = coalesce(mega_map.pokeapi_form_name, seed_map.pokeapi_form_name)
