# Release Data

This directory is reserved for versioned release CSV packages.

Intended contents:

- one subdirectory per published `dataset_version` (e.g. `0.1.0/`)
- inside each: the eight core-entity CSVs listed in
  `docs/dataset-spec.md`'s "Release package" section (`pokemon.csv`,
  `pokemon_stat_canonical.csv`, `pokemon_stat_champions.csv`,
  `pokemon_stat_delta.csv`, `legality_snapshot.csv`,
  `tournament_event.csv`, `tournament_team.csv`,
  `tournament_team_member.csv`)

Populated by `python -m pipelines.cli release --version <dataset_version>`,
which copies `data/normalized/*.csv` here — gated on
`reports/validation/validation_report.json` reporting zero
`release_blocking_findings`. See `releases/manifests/` and
`releases/changelogs/` for the accompanying manifest and changelog each
release also publishes.
