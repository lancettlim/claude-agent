# Product Requirements Document (PRD)

## Product name
Pokémon Champions Competitive Data Platform

## Document status
Draft v1.0

## Problem statement
Competitive Pokémon Champions data is fragmented across canonical game sources, format-specific balance sources, and tournament/team archives. Analysts, creators, and players must manually gather and normalize this information before they can run useful competitive analysis.

## Product vision
Provide a single, trustworthy, and regularly updated data product for Pokémon Champions that combines canonical game data, format-specific rule/balance data, and tournament usage intelligence.

## Goals
- Create one unified dataset with stable schemas and documented lineage.
- Reduce manual data collection effort for users by at least 80%.
- Enable repeatable analysis for legality, balance deltas, usage trends, and team composition patterns.
- Publish predictable update cadences aligned with format and tournament changes.

## Non-goals
- Building a full public consumer-facing battle simulator.
- Real-time ingestion of every live match.
- Replacing source-of-truth ownership from original platforms.

## Target users
- **Competitive analysts**: need clean, queryable historical and current metagame data.
- **Content creators**: need reliable trend snapshots and supporting stats.
- **Team builders/coaches**: need legal pool validation, usage patterns, and matchup context.
- **Internal product teams**: need stable data contracts for downstream dashboards or tools.

## Success metrics
- Dataset freshness SLA met in >=95% of scheduled updates.
- <=1% critical schema/data integrity errors per monthly release.
- >=70% reduction in ingestion-to-analysis lead time for internal users.
- Adoption: at least 3 recurring downstream consumers in first phase.

## Scope
### In scope (Phase 1)
- Source ingestion from:
  - PokéAPI (canonical data)
  - OP.GG Pokémon Champions (format-specific balance/legal pool)
  - PokéBase app (regulation and restrictions context)
  - MunchStats / Limitless / Victory Road (tournament and team data)
- Normalized core entities:
  - Pokémon, forms, stats, moves, items, abilities, legal status
  - Tournament event, player, team, team member, placements
- Change-tracking layer:
  - Canonical vs Champions stat deltas
  - Regulation-aware legality snapshots
- Documentation:
  - Data dictionary
  - Source lineage and extraction notes
  - Refresh cadence and known limitations

### Out of scope (Phase 1)
- Advanced predictive modeling APIs
- Full web application UX
- Community write-back/edit workflows

## Functional requirements
1. System must ingest each source into staging with source timestamp metadata.
2. System must normalize records into consistent IDs and join keys.
3. System must store both canonical values and Champions-modified values where relevant.
4. System must expose regulation-aware legality fields by snapshot date.
5. System must preserve tournament provenance (event/source/date) for all team and placement records.
6. System must produce exportable flat files for analysis use (CSV/JSON).
7. System must publish schema and field definitions with every release.

## Non-functional requirements
- **Reliability**: deterministic transformations; reproducible outputs.
- **Traceability**: every record mapped to source and extraction run.
- **Maintainability**: modular extraction/transformation steps per source.
- **Compliance**: no unauthorized redistribution of protected content; attribution retained.

## User stories
- As an analyst, I can compare canonical vs Champions stats by Pokémon and form.
- As a team builder, I can filter legal Pokémon by current regulation and item constraints.
- As a creator, I can query top-used cores and moves from recent tournaments.
- As a data consumer, I can trust that each field has clear definitions and provenance.

## Milestones
1. **M1 – Data contract definition**
   - Finalize schema and entity relationships.
2. **M2 – Source ingestion baseline**
   - Land repeatable extraction for all identified sources.
3. **M3 – Normalization and delta layer**
   - Deliver canonical-vs-Champions diff outputs.
4. **M4 – Tournament enrichment**
   - Integrate event/team/player structures.
5. **M5 – Release readiness**
   - Publish v1 dataset package + documentation.

## Risks and mitigations
- **Source structure changes** → Add source-specific validation checks and fallback parsing.
- **Data licensing/usage ambiguity** → Track attribution and limit distribution scope where required.
- **ID mismatches across sources** → Maintain mapping tables and confidence flags.
- **Coverage gaps in tournament data** → Use multi-source triangulation and completeness scoring.

## Open questions
- What is the minimum acceptable refresh cadence per source?
- Which downstream interface is prioritized first (files only vs query endpoint)?
- What governance is needed for schema versioning and deprecations?
