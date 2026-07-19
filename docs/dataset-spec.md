# V1 Dataset Spec

This document is the authoritative v1 dataset artifact plan, distinct from
the repository-level overview in `README.md`.

## Immediate objective

- **Decision**: move from docs-only research to a documented v1 data artifact
  spec that can be executed in phases.
- **Near-term output**: a reproducible, versioned dataset package with
  canonical stats, Champions deltas, legality snapshots, and tournament usage
  records.

## V1 scope (selected high-confidence sources)

The v1 scope covers four sources from `data-sources.md`:

1. **PokéAPI** (canonical base data)
2. **OP.GG Pokémon Champions** (format-specific legal pool and rebalanced data)
3. **MunchStats** (structured tournament roster/usage data)
4. **PokéBase app** (per-regulation legal-pool membership)

PokéBase was originally deferred ("defer until regulation-specific
restrictions are needed beyond the OP.GG legal pool snapshot") but was
pulled into v1 once that need became concrete: OP.GG's Champions Pokédex
page publishes only a single regulation-agnostic legal pool, so
`legality_snapshot.regulation_code` — a locked required field — had no
in-scope source and was permanently null. PokéBase's page embeds real,
per-Pokémon regulation-set membership and turned out to be scriptable the
same way OP.GG is (see `pipelines/extract/pokebase.py`'s docstring), so it
now supplies `legality_snapshot` directly; OP.GG remains the source for
`pokemon_stat_champions`'s stats and overall legal-pool flag.

These four sources provide strong coverage of canonical values, format
modifications, regulation-aware legality, and real competitive usage while
keeping ingestion complexity manageable for v1.

## Deferred sources

The following sources remain useful for later phases but are explicitly deferred
from v1 ingestion and release requirements:

- **Limitless VGC** — defer until historical event coverage expansion
- **Victory Road** — defer until detailed moveset/EV enrichment is prioritized

## Target v1 schema and data contract

### Entity dictionary

- `pokemon`
  - **Purpose**: canonical identity table for Pokémon and form references used by
    all downstream entities
  - **Primary key**: `pokemon_key`
  - **Join keys**: `pokemon_id`, `form_name`
  - **Required fields**: `pokemon_key`, `pokemon_id`, `pokemon_name`,
    `form_name`, `source_name`, `source_url`, `source_record_id`,
    `extracted_at_utc`, `dataset_version`
- `pokemon_stat_canonical`
  - **Purpose**: canonical PokéAPI stat snapshot
  - **Primary key**: `pokemon_stat_canonical_key`
  - **Join keys**: `pokemon_key`, `pokemon_id`
  - **Required fields**: `pokemon_stat_canonical_key`, `pokemon_key`,
    `pokemon_id`, `hp`, `attack`, `defense`, `sp_attack`, `sp_defense`,
    `speed`, `stat_total`, `source_name`, `source_url`, `source_record_id`,
    `extracted_at_utc`, `dataset_version`
- `pokemon_stat_champions`
  - **Purpose**: Champions-format stat snapshot from OP.GG
  - **Primary key**: `pokemon_stat_champions_key`
  - **Join keys**: `pokemon_key`, `pokemon_id`
  - **Required fields**: `pokemon_stat_champions_key`, `pokemon_key`,
    `pokemon_id`, `hp`, `attack`, `defense`, `sp_attack`, `sp_defense`,
    `speed`, `stat_total`, `is_legal`, `source_name`, `source_url`,
    `source_record_id`, `extracted_at_utc`, `dataset_version`
- `pokemon_stat_delta`
  - **Purpose**: derived canonical-vs-Champions stat change output
  - **Primary key**: `pokemon_stat_delta_key`
  - **Join keys**: `pokemon_key`, `pokemon_id`
  - **Required fields**: `pokemon_stat_delta_key`, `pokemon_key`, `pokemon_id`,
    `hp_delta`, `attack_delta`, `defense_delta`, `sp_attack_delta`,
    `sp_defense_delta`, `speed_delta`, `stat_total_delta`,
    `canonical_dataset_version`, `champions_dataset_version`, `source_name`,
    `source_url`, `extracted_at_utc`, `dataset_version`
- `legality_snapshot`
  - **Purpose**: time-sliced, regulation-aware legal status for the
    Champions pool, sourced from PokéBase (see "PokéBase" below)
  - **Primary key**: `legality_snapshot_key`
  - **Join keys**: `pokemon_key`, `pokemon_id`, `regulation_code`, `snapshot_date`
  - **Required fields**: `legality_snapshot_key`, `pokemon_key`, `pokemon_id`,
    `regulation_code`, `is_legal`, `snapshot_date`, `source_name`,
    `source_url`, `source_record_id`, `extracted_at_utc`, `dataset_version`
- `tournament_event`
  - **Purpose**: normalized tournament metadata from MunchStats
  - **Primary key**: `event_id`
  - **Join keys**: `event_id`
  - **Required fields**: `event_id`, `event_name`, `event_date`, `source_name`,
    `source_url`, `source_record_id`, `extracted_at_utc`, `dataset_version`
  - **Optional fields**: `event_tier` (tournament tier, e.g. International/
    Regional/Special — nullable since MunchStats doesn't report it for
    every event)
- `tournament_team`
  - **Purpose**: team-level tournament metadata
  - **Primary key**: `team_id`
  - **Join keys**: `event_id`, `player_id`, `team_id`
  - **Required fields**: `team_id`, `event_id`, `player_id`, `placement`,
    `source_name`, `source_url`, `source_record_id`, `extracted_at_utc`,
    `dataset_version`
  - **Optional fields**: `record_wins`, `record_losses` (win-rate proxy —
    nullable since MunchStats doesn't report a record for every player)
- `tournament_team_member`
  - **Purpose**: one row per Pokémon on a normalized tournament team
  - **Primary key**: `team_member_id`
  - **Join keys**: `team_id`, `event_id`, `pokemon_key`, `pokemon_id`
  - **Required fields**: `team_member_id`, `team_id`, `event_id`, `pokemon_key`,
    `pokemon_id`, `slot_number`, `source_name`, `source_url`,
    `source_record_id`, `extracted_at_utc`, `dataset_version`
  - **Optional fields**: `item_name`, `ability`, `tera_type`, `moves`
    (pipe-delimited) — nullable since MunchStats doesn't report a full
    build for every roster slot

### Locked required fields

- **Identity**: `pokemon_id`, `pokemon_name`, `form_name`
- **Stat context**: `hp`, `attack`, `defense`, `sp_attack`, `sp_defense`,
  `speed`, `stat_total`
- **Legality context**: `regulation_code`, `is_legal`, `snapshot_date`
- **Tournament context**: `event_id`, `event_name`, `event_date`, `player_id`,
  `team_id`, `placement`
- **Lineage/provenance**: `source_name`, `source_url`, `extracted_at_utc`,
  `source_record_id`, `dataset_version`

### Key rules

- `pokemon_key` is the normalized cross-source identifier for one
  Pokémon/form record.
- `pokemon_id` stores the canonical Pokédex identifier used as the preferred
  mapping key across sources.
- Derived tables must retain enough identifiers to trace both upstream records
  and published release versions.
- Rows that cannot be mapped to a stable `pokemon_key` may remain in staging but
  must not ship in release outputs without an explicit confidence override.

### Refresh policy

- **PokéAPI**: weekly scheduled refresh
- **OP.GG Pokémon Champions**: daily change check, publish on change detection
- **MunchStats**: daily check with publish after new tournament/event detection
- **Versioning rule**: publish `dataset_version` on every successful refresh
  cycle with changelog notes for schema or major row-count shifts

### Provenance rules

- Every record must include source metadata and extraction timestamp.
- Derived tables (for example deltas) must preserve upstream source references.
- Records without traceable source identity are excluded from release outputs.

## Release package

Each v1 release must publish a versioned package with:

- `pokemon.csv`
- `pokemon_stat_canonical.csv`
- `pokemon_stat_champions.csv`
- `pokemon_stat_delta.csv`
- `legality_snapshot.csv`
- `tournament_event.csv`
- `tournament_team.csv`
- `tournament_team_member.csv`
- `manifest.json`
- `CHANGELOG.md`

### Manifest contents

`manifest.json` must include:

- `dataset_version`
- `published_at_utc`
- `sources` with per-source name, URL, extraction timestamp, and record counts
- `tables` with row counts, primary key definitions, and file names
- `quality_checks` with pass/fail status and metric values
- `known_limitations`

### Dataset version semantics

- Use semantic-style dataset versions: `MAJOR.MINOR.PATCH`
- Increment **MAJOR** for breaking schema changes
- Increment **MINOR** for new tables, fields, or materially expanded coverage
- Increment **PATCH** for refresh-only releases with no schema changes

### Changelog expectations

Every release entry must summarize:

- source refresh dates
- schema changes
- major row-count changes
- newly known limitations or resolved limitations

## Source-specific extraction contracts

### PokéAPI

- **Records to capture**
  - Pokémon/form identity rows
  - Base stat rows for all Pokémon in the mapped Champions pool
- **Refresh cadence**
  - Weekly scheduled refresh
- **Mapping rules**
  - Treat PokéAPI numeric IDs as the canonical `pokemon_id`
  - Normalize form naming into the shared `form_name` convention
- **Known risks**
  - Form-name mismatches between canonical and format-specific sources
  - Multi-form species that need explicit mapping rather than name-only joins

### OP.GG Pokémon Champions

- **Records to capture**
  - Legal pool membership
  - Rebalanced stat values for each listed Pokémon/form
- **Refresh cadence**
  - Daily change detection; publish only when the legal pool or stats change
- **Mapping rules**
  - Join to canonical records by numeric ID where available
  - Fall back to controlled name/form mappings when direct ID mapping is absent
- **Known risks**
  - HTML structure volatility
  - Custom form labels that may not match canonical naming

### MunchStats

- **Records to capture**
  - Tournament metadata
  - Team metadata
  - Team-member Pokémon rows
- **Refresh cadence**
  - Daily check with publish after new event detection
- **Mapping rules**
  - Preserve upstream event and roster identifiers as `source_record_id`
  - Map roster Pokémon names to canonical `pokemon_id` and `pokemon_key`
- **Known risks**
  - Incomplete tournament coverage
  - Roster naming inconsistencies that reduce automated match confidence

### PokéBase

- **Records to capture**
  - Per-regulation legal-pool membership for the Champions format
    (`legality_snapshot`'s sole source — see "V1 scope" above for why OP.GG
    doesn't cover this)
- **Refresh cadence**
  - Daily change detection; publish only on regulation or legal-pool change
- **Mapping rules**
  - Use PokéBase's own `nationalNumber` directly as `pokemon_id` (correct
    for Mega/regional/alternate forms too, unlike OP.GG's fabricated
    per-form ids)
  - Join to canonical records by form slug, which already matches PokéAPI's
    own form-naming convention for the large majority of entries; fall back
    to controlled name/form mappings (PokéAPI's designated default variety
    per species) for the remainder
- **Known risks**
  - HTML structure volatility
  - Only positive (legal) regulation membership is published — there's no
    explicit "removed from this regulation" signal, so a Pokémon's absence
    from a snapshot isn't distinguishable from "not yet observed" versus
    "confirmed illegal"

### Confidence requirements

- OP.GG legal-pool mapping coverage must reach at least 95% before release.
- Tournament team-member mapping coverage must reach at least 90% before
  release.
- PokéBase legal-pool mapping coverage must reach at least 95% before
  release.
- Any unmapped or low-confidence rows must be documented in the manifest and
  excluded from release tables unless explicitly approved.

## Phased execution roadmap

v1 delivery is sequenced into three phases — **ingestion**, **normalization**,
and **analytics/dashboard outputs**. See `todo.md` for the task-level
checklist and current status of each phase.

## Validation and release gates

- **Coverage**
  - `>=95%` of OP.GG legal pool mapped to canonical `pokemon_id`
  - `>=90%` of targeted tournament records mapped to normalized team tables
  - `>=95%` of PokéBase legal-pool rows mapped to canonical `pokemon_id`
- **Null-rate gate**
  - Required-field null rate must be `<=1%` for every core table
- **Duplicate-key gate**
  - Duplicate primary-key violations must equal `0`
- **Referential-integrity gate**
  - `pokemon_stat_*` rows must resolve to `pokemon`
  - `legality_snapshot` rows must resolve to `pokemon`
  - `tournament_team` rows must resolve to `tournament_event`
  - `tournament_team_member` rows must resolve to both `tournament_team` and
    `pokemon`

The v1 definition-of-done checklist that tracks these gates, plus export and
example-query validation, lives in `todo.md`.

## Next implementation task

After document alignment, create the repository structure for:

- staging snapshots
- normalized outputs
- release manifests
- release changelogs
- validation reports
