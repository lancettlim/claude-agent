# claude-agent

This repository now targets building the first usable Pokémon Champions dataset
artifact (v1), not only source curation documentation.

## Immediate objective

- **Decision**: move from docs-only research to a documented v1 data artifact
  spec that can be executed in phases.
- **Near-term output**: a reproducible, versioned dataset package with canonical
  stats, Champions deltas, legality snapshots, and tournament usage records.

## V1 scope (selected high-confidence sources)

The v1 scope is intentionally limited to three sources from `DATASET.md`:

1. **PokéAPI** (canonical base data)
2. **OP.GG Pokémon Champions** (format-specific legal pool and rebalanced data)
3. **MunchStats** (structured tournament roster/usage data)

These three sources provide strong coverage of canonical values, format
modifications, and real competitive usage while keeping ingestion complexity
manageable for v1.

## Target v1 schema and data contract

### Core entities

- `pokemon` (one row per Pokémon/form reference)
- `pokemon_stat_canonical` (canonical stat snapshot from PokéAPI)
- `pokemon_stat_champions` (Champions-specific stat snapshot from OP.GG)
- `pokemon_stat_delta` (computed canonical vs Champions changes)
- `legality_snapshot` (regulation/time-sliced legal status)
- `tournament_event` (event metadata)
- `tournament_team` (team-level roster metadata)
- `tournament_team_member` (per-Pokémon team membership and competitive fields)

### Required fields (minimum)

- **Identity**: `pokemon_id`, `pokemon_name`, `form_name`
- **Stat context**: `hp`, `attack`, `defense`, `sp_attack`, `sp_defense`,
  `speed`, `stat_total`
- **Legality context**: `regulation_code`, `is_legal`, `snapshot_date`
- **Tournament context**: `event_id`, `event_name`, `event_date`, `player_id`,
  `team_id`, `placement`
- **Lineage/provenance**: `source_name`, `source_url`, `extracted_at_utc`,
  `source_record_id`, `dataset_version`

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

## Phased execution roadmap

### Phase 1 — Ingestion

- Implement source extraction contracts for PokéAPI, OP.GG, and MunchStats.
- Land staging outputs with raw snapshots and extraction metadata.
- Validate source availability and row-level parsing success thresholds.

### Phase 2 — Normalization

- Standardize IDs and join keys across canonical, Champions, and tournament
  datasets.
- Build canonical vs Champions delta outputs.
- Generate regulation-aware legality snapshots.

### Phase 3 — Analytics and dashboard outputs

- Publish flat analytical exports and summary aggregates.
- Provide dashboard-ready trend tables for usage, legality, and stat changes.
- Document KPI views and filter dimensions (regulation/date/tournament tier).

## V1 definition of done

- [ ] **Coverage**
  - [ ] >=95% of OP.GG legal pool mapped to canonical `pokemon_id`
  - [ ] >=90% of targeted tournament records mapped to normalized team tables
- [ ] **Data quality checks**
  - [ ] Required-field null rate <=1% for core tables
  - [ ] Duplicate primary-key violations = 0
  - [ ] Referential integrity checks pass for Pokémon/team/event joins
- [ ] **Export package**
  - [ ] Versioned CSV outputs for all core entities
  - [ ] Versioned JSON metadata manifest with source lineage + run stats
- [ ] **Example analysis queries validated**
  - [ ] Which Pokémon gained/lost the most total stats vs canonical?
  - [ ] Which legal Pokémon appear most in recent tournament teams?
  - [ ] Which regulations show the largest legal-pool changes over time?

## Dataset resources

- `DATASET.md` — curated external sources for canonical Pokémon data,
  Pokémon Champions format data, tournament results, and team-building
  references
- `PRD.md` — product requirements document for the Pokémon Champions
  competitive data platform
- `champions-business-case.md` — supporting business case document

## Implementation scaffold

The repository now includes a runnable Python scaffold for the v1 dataset pipeline.

### Scaffold components

- `pyproject.toml` — project packaging and CLI entrypoint
- `configs/pipeline.json` — central source metadata and refresh settings
- `src/champions_dataset/` — ingestion, normalization, export, validation, and shared runtime modules
- `schemas/v1/` — versioned contracts for core entities and run manifests
- `docs/implementation-scaffold.md` — implementation layout and phase mapping
- `docs/data-dictionary-template.md` — starter data dictionary for required fields
- `.github/workflows/` — validation and scheduled-refresh placeholders

### Quickstart

```bash
python -m pip install -e .
champions-dataset --phase all --dry-run
champions-dataset --phase validate --dry-run
```

The current CLI emits planned manifests and validation results so implementation can proceed phase-by-phase without live extraction logic yet.

