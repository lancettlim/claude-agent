# Changelog — dataset_version 0.3.0

Published: 2026-08-03T09:02:19Z

## Source refresh dates

- PokéAPI: 2026-08-03T08:26:36.523413+00:00
- OP.GG Pokémon Champions: 2026-08-03T08:26:02.917650+00:00
- MunchStats: 2026-08-03T08:46:08.010721+00:00
- PokéBase: 2026-08-03T08:26:06.404790+00:00
- Bulbagarden Archives: 2026-08-03T08:26:08.595486+00:00

## Schema changes

- {None | describe added/removed/changed fields or tables}

## Row-count changes

- {table_name}: {previous_row_count} -> {new_row_count}

## Known limitations

### New

- PokéBase publishes only positive legality signals, so legality_snapshot cannot distinguish a Pokémon that was banned in a later regulation from one not yet observed; legality_summary_by_regulation's cumulative count can only grow.
- Every mapped Pokémon has a stat_total_delta of exactly 0: no Champions rebalance has occurred yet. This is real data, not a defect.
- A small number of ambiguous source-to-form mappings are deliberately excluded rather than guessed, including OP.GG's and Bulbagarden's 'Mega Meowstic' entries.
- tournament_match records team-vs-team outcomes, not Pokemon-vs-Pokemon. No source publishes a per-battle log naming which four of a team's six Pokemon were brought, so pokemon_head_to_head attributes each result to the whole roster.
- No EV or IV spreads are published by any source in scope: official tournament team sheets carry ability, held item, nature and moves only. team_list_member therefore has no EV fields.
- Limitless VGC publishes team lists for the day-2 cut only (156 of 1096 players at NAIC 2026), so team_list/team_list_member are a top-cut view rather than full-field coverage.

### Resolved

- {describe limitations from prior versions that no longer apply}
