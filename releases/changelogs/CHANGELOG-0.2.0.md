# Changelog — dataset_version 0.2.0

Published: 2026-07-21T11:20:51Z

## Source refresh dates

- PokéAPI: 2026-07-21T11:17:17.414942+00:00
- OP.GG Pokémon Champions: 2026-07-21T11:19:05.199378+00:00
- MunchStats: 2026-07-21T11:15:55.840997+00:00
- PokéBase: 2026-07-21T11:19:19.455781+00:00
- Bulbagarden Archives: 2026-07-21T11:16:38.103977+00:00

## Schema changes

- {None | describe added/removed/changed fields or tables}

## Row-count changes

- {table_name}: {previous_row_count} -> {new_row_count}

## Known limitations

### New

- Only positive (legal) regulation membership is published by PokéBase — absence of a row doesn't necessarily confirm a Pokémon is illegal, just that no legal membership was observed.
- pokemon_stat_champions/pokemon_stat_delta show zero stat deltas for every mapped Pokémon in this snapshot — OP.GG's Champions stats currently match PokéAPI's canonical base stats exactly; not a bug, see dbt/analyses/README.md.
- OP.GG's 'mega-meowstic', PokéBase's 'meowstic-mega'/'tauros-paldea', and Bulbagarden's 'Mega Meowstic' sprite title are all excluded from mapping: genuinely ambiguous between multiple PokéAPI forms (meowstic-male-mega vs. meowstic-female-mega), not guessed.

### Resolved

- None
