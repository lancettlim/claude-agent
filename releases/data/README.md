# Release Data

This directory is reserved for versioned release CSV packages.

Intended contents:

- one subdirectory per published `dataset_version` (e.g. `0.1.0/`)
- inside each: the nine core-entity CSVs listed in
  `docs/dataset-spec.md`'s "Release package" section (`pokemon.csv`,
  `pokemon_stat_canonical.csv`, `pokemon_stat_champions.csv`,
  `pokemon_stat_delta.csv`, `legality_snapshot.csv`,
  `tournament_event.csv`, `tournament_team.csv`,
  `tournament_team_member.csv`, `pokemon_asset.csv`), plus an `images/`
  directory holding the sprite files `pokemon_asset.csv` references

Populated by `python -m pipelines.cli release --version <dataset_version>`,
which copies `data/normalized/*.csv` here — gated on
`reports/validation/validation_report.json` reporting zero
`release_blocking_findings`. See `releases/manifests/` and
`releases/changelogs/` for the accompanying manifest and changelog each
release also publishes.

**Image redistribution note**: `images/` files are sourced from Bulbagarden
Archives, a fan wiki hosting Pokémon sprite artwork that is ultimately
Nintendo/Game Freak-owned. Bundling them into a versioned, redistributable
release package is a different posture than a fan wiki hosting them for
reference use, and that posture hasn't had a formal legal review — treat
this as a documented known limitation (see each release's `manifest.json`
`known_limitations` and `CHANGELOG-<version>.md`), not a cleared
redistribution right.
