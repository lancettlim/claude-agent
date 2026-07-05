# Data dictionary template

## Core entities

| Entity | Purpose | Required lineage fields |
| --- | --- | --- |
| `pokemon` | Canonical Pokémon/form identity reference | `source_name`, `source_url`, `extracted_at_utc`, `source_record_id`, `dataset_version` |
| `pokemon_stat_canonical` | Baseline canonical stat snapshot | `source_name`, `source_url`, `extracted_at_utc`, `source_record_id`, `dataset_version` |
| `pokemon_stat_champions` | Champions-specific stat snapshot | `source_name`, `source_url`, `extracted_at_utc`, `source_record_id`, `dataset_version` |
| `pokemon_stat_delta` | Derived canonical-versus-Champions deltas | `source_name`, `source_url`, `extracted_at_utc`, `source_record_id`, `dataset_version` |
| `legality_snapshot` | Regulation-aware legality view | `source_name`, `source_url`, `extracted_at_utc`, `source_record_id`, `dataset_version` |
| `tournament_event` | Event-level tournament metadata | `source_name`, `source_url`, `extracted_at_utc`, `source_record_id`, `dataset_version` |
| `tournament_team` | Team-level roster metadata | `source_name`, `source_url`, `extracted_at_utc`, `source_record_id`, `dataset_version` |
| `tournament_team_member` | Team member usage records | `source_name`, `source_url`, `extracted_at_utc`, `source_record_id`, `dataset_version` |

## Required field set

- `pokemon_id`
- `pokemon_name`
- `form_name`
- `hp`
- `attack`
- `defense`
- `sp_attack`
- `sp_defense`
- `speed`
- `stat_total`
- `regulation_code`
- `is_legal`
- `snapshot_date`
- `event_id`
- `event_name`
- `event_date`
- `player_id`
- `team_id`
- `placement`
- `source_name`
- `source_url`
- `extracted_at_utc`
- `source_record_id`
- `dataset_version`
