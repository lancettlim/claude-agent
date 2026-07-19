# Changelog — dataset_version 0.1.0

Published: 2026-07-19T06:22:57Z

## Source refresh dates

- PokéAPI: 2026-07-18T17:21:32.693897+00:00
- OP.GG Pokémon Champions: 2026-07-18T17:06:37.536825+00:00
- MunchStats: 2026-07-18T17:06:38.505628+00:00
- PokéBase: 2026-07-19T06:15:49.510565+00:00

## Schema changes

- {None | describe added/removed/changed fields or tables}

## Row-count changes

- {table_name}: {previous_row_count} -> {new_row_count}

## Known limitations

### New

- Only positive (legal) regulation membership is published by PokéBase — absence of a row doesn't necessarily confirm a Pokémon is illegal, just that no legal membership was observed.
- pokemon_stat_champions/pokemon_stat_delta show zero stat deltas for every mapped Pokémon in this snapshot — OP.GG's Champions stats currently match PokéAPI's canonical base stats exactly; not a bug, see dbt/analyses/README.md.
- OP.GG's 'mega-meowstic' and PokéBase's 'meowstic-mega'/'tauros-paldea' entries are excluded from mapping: genuinely ambiguous between multiple PokéAPI forms, not guessed.

### Resolved

- {describe limitations from prior versions that no longer apply}
