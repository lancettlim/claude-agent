-- Resolves each stg_opgg_champions row to a pokemon_key/pokemon_id via the
-- opgg_key_to_pokeapi_form seed (dataset-spec.md's OP.GG mapping rule:
-- "Join to canonical records by numeric ID where available. Fall back to
-- controlled name/form mappings when direct ID mapping is absent" — the
-- seed covers both: most OP.GG keys already equal a real PokéAPI form_name
-- directly, so this single join handles the common case and the
-- mega-prefix/regional-suffix/default-form fallback cases alike). Rows
-- that resolve to no seed entry are dropped: per dataset-spec.md, "Rows
-- that cannot be mapped to a stable pokemon_key may remain in staging but
-- must not ship in release outputs without an explicit confidence
-- override." Shared by pokemon_stat_champions and legality_snapshot.
with resolved as (
  select
    source.*,
    pokemon.pokemon_key as resolved_pokemon_key,
    pokemon.pokemon_id as resolved_pokemon_id
  from {{ ref('stg_opgg_champions') }} source
  inner join {{ ref('opgg_key_to_pokeapi_form') }} seed_map
    on seed_map.opgg_key = source.source_record_id
  inner join {{ ref('pokemon') }} pokemon
    on pokemon.form_name = seed_map.pokeapi_form_name
)

-- OP.GG lists a handful of species (e.g. Vileplume, Blaziken, Staraptor,
-- Pyroar) as two separate Pokédex entries for cosmetic male/female sprite
-- differences that PokéAPI doesn't model as distinct forms, so both rows
-- resolve to the same pokemon_key. Their stats are identical either way;
-- keep the non-female/male-suffixed row deterministically so pokemon_key
-- stays unique downstream.
select
  * exclude (_dedup_rank)
from (
  select
    *,
    row_number() over (
      partition by resolved_pokemon_key
      order by (
        case when source_record_id like '%-female' or source_record_id like '%-male' then 1 else 0 end
      )
    ) as _dedup_rank
  from resolved
)
where _dedup_rank = 1
