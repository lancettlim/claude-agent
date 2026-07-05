# Pokemon Champions Analytics Platform Business Case

Date: 2026-06-28
Audience: Competitive players and community contributors
Purpose: Strategic rationale for advancing this repository from canonical data foundation to near-term Champions competitive intelligence outputs

## 1) Executive Summary

Pokemon Champions competition is data-rich but workflow-poor. Players currently combine legal pool rules, custom stat changes, speed tiers, and usage signals from fragmented sources, which increases prep time and decision error risk during the team selection phase.

This repository already provides a strong technical base: canonical Pokemon normalization, reproducible QA gates, and an analytics warehouse path. The near-term business opportunity is to add the Champions layer (legal pool, source crosswalks, drift-safe refresh, release manifest) so competitive users can rely on one trustworthy dataset rather than manual spreadsheets.

The strategic case is strong for three reasons:
1. Timing: the Champions ecosystem is active and source-fragmented, creating immediate demand for normalized data.
2. Feasibility: foundational pipeline and QA controls are already implemented and aligned to id-first joins and provenance rules.
3. Value: even conservative adoption yields substantial time-value savings for players, with optional monetization paths to sustain operations.

Recommended decision: execute a 12-month phased plan, prioritizing the near-term Champions data layer in the next 3 sprints, then expand into strategist-ready decision outputs.

## 2) Problem and Opportunity

### Current User Problem

Competitive players and analysts face four operational constraints:
1. Source fragmentation across OP.GG, Pokebase, MunchStats, Limitless, and Victory Road.
2. Cross-source identity mismatches for forms and naming variants.
3. Frequent manual refresh and validation effort when regulations shift.
4. Limited trust in ad hoc merged datasets without provenance and quality gates.

Result: higher preparation overhead and inconsistent team-selection decisions.

### Why Now

Pokemon Champions introduces custom rules and altered competitive context (including restricted legal pools and source-specific mechanics). This increases the cost of relying on base-game-only datasets and creates urgency for a dedicated Champions analytics layer.

### Opportunity Statement

Build the default community data backbone for Pokemon Champions team selection by combining:
1. Canonical baseline ownership (local raw snapshots).
2. Source-owned competitive enrichments.
3. Release-grade QA and refresh governance.

## 3) Solution Definition (Current App + Near-Term Scope)

### What Exists Today (Implemented)

The application currently delivers:
1. Canonical normalization from local raw snapshots to analysis-ready CSV outputs.
2. Quality gates for uniqueness, required fields, and join coverage.
3. Analysis tables and dbt warehouse path for reproducible local analytics.
4. Consolidated pipeline entry command for normalization, QA, and optional dbt refresh.

Business implication: execution risk is reduced because critical foundation work is complete.

### What Near-Term Scope Adds (Roadmap)

Near-term implementation focuses on the Champions data layer:
1. Champions legal pool table keyed by numeric pokemon_id.
2. Form and name crosswalk mapping process.
3. Extended QA for canonical-to-Champions coverage and drift checks.
4. Run-level release manifest with provenance and pass/fail state.

Business implication: this scope creates immediate player utility without waiting for full strategist automation.

### Out of Scope for This Business Case Window

1. End-user dashboard productization.
2. Real-time streaming ingestion.
3. Full battle-time adaptive recommendation engine.

## 4) Strategic Fit for Competitive Players and Community

### User Value by Segment

1. Individual competitor:
- Faster pre-match preparation.
- Better confidence in legal pool and matchup context.
- Fewer avoidable errors from stale or conflicting sources.

2. Team coach and analyst:
- Shared source of truth for prep workflows.
- Repeatable refresh process before events.
- Easier post-event metagame review.

3. Content creator:
- Faster evidence-backed publishing cycles.
- Better transparency and provenance for audience trust.

### Positioning

This project should position as a reliability-first analytics substrate, not another static tier list.

Differentiators:
1. Id-first integration discipline.
2. Explicit source ownership per metric.
3. QA-blocked publish behavior with manifests.
4. Clear separation of canonical versus competitive enrichments.

## 5) Financial Model

## 5.1 Modeling Approach

Because this initiative can serve community value before direct monetization, this case uses two lenses:
1. Community productivity value (time and decision support impact).
2. Operator sustainability economics (what it takes to keep the platform healthy).

Currency: USD
Horizon: Year 1 (build + initial operation)

## 5.2 Assumptions

### Adoption and usage assumptions

1. Addressable active competitive community: 25,000 players.
2. Year-1 active adoption rates:
- Conservative: 2 percent (500 users)
- Base: 5 percent (1,250 users)
- Aggressive: 10 percent (2,500 users)
3. Team-prep sessions per active user per month: 8.
4. Time saved per prep session versus manual source stitching: 20 minutes.
5. Value of player time: 20 per hour.
6. Additional decision-support value proxy (reduced avoidable prep mistakes, better bring confidence): 60 per active user per year.

### Cost assumptions

1. Build phase staffing (first 6 months):
- Data engineering: 0.8 FTE at 14,000 per month.
- Analytics engineering: 0.6 FTE at 14,000 per month.
- Strategy domain advisor: 0.2 FTE at 12,000 per month.
2. Build tooling and misc operations (first 6 months): 3,000.
3. Operate phase staffing (next 6 months):
- Reliability and refresh operations: 0.4 FTE at 14,000 per month.
4. Operate infra and QA/comms reserve (next 6 months): 14,000.

Estimated Year-1 total cost:
- Build staffing: 132,000
- Build tooling: 3,000
- Operate staffing: 33,600
- Operate infra and reserve: 14,000
- Total: 182,600

## 5.3 Scenario Calculations

### Formula set

1. Annual prep hours saved per user = 8 sessions x 12 months x (20/60) hours = 32 hours
2. Annual time-value per user = 32 x 20 = 640
3. Annual total value per user = 640 + 60 = 700
4. Annual gross community value = Active users x 700
5. Net strategic value = Annual gross community value - Year-1 cost

### Scenario outcomes

| Scenario | Active Users | Gross Community Value | Year-1 Cost | Net Strategic Value |
|---|---:|---:|---:|---:|
| Conservative | 500 | 350,000 | 182,600 | 167,400 |
| Base | 1,250 | 875,000 | 182,600 | 692,400 |
| Aggressive | 2,500 | 1,750,000 | 182,600 | 1,567,400 |

Interpretation:
1. The case remains positive even under conservative adoption.
2. Most value creation comes from reducing recurring prep friction.
3. Reliability investments are justified because trust drives repeat usage.

## 5.4 Break-even Logic and Sensitivity

### Strategic break-even threshold

Required active users for strategic break-even:
- 182,600 / 700 = approximately 261 active users

This threshold is materially below the conservative scenario (500 users), suggesting favorable downside protection if adoption assumptions are directionally accurate.

### Most sensitive variables

1. Time saved per prep session.
2. Active adoption rate.
3. Trust and retention (which depend on QA pass rates and freshness).

If time saved drops from 20 to 12 minutes, value per user falls from 700 to 444. Even then, break-even active users are approximately 412, still below the conservative scenario.

## 5.5 Sustainability Options (Optional Revenue)

To sustain operations without reducing quality:
1. Community-supported model (donations and sponsorships).
2. Pro analyst tier (advanced exports and scheduled query packs).
3. B2B data feeds for coaches, creators, and tournament media.

Revenue is not required for strategic value creation but can de-risk long-term maintenance.

## 6) Risks and Mitigation Plan

### Risk 1: External source schema volatility

Impact: high
Mitigation:
1. Adapter-level schema checks.
2. Fail-fast behavior by source.
3. Release blocked until parser and mapping are reconciled.

### Risk 2: Silent join loss from naming and form mismatches

Impact: critical
Mitigation:
1. Mandatory crosswalk mappings.
2. Coverage QA between canonical and Champions identifiers.
3. Unresolved mapping report per run.

### Risk 3: Ownership conflicts for overlapping metrics

Impact: medium-high
Mitigation:
1. Single-owner metric policy in source catalog.
2. Release review checklist for conflict detection.

### Risk 4: Community trust gap in outputs

Impact: medium-high
Mitigation:
1. Provenance fields on outputs.
2. Published QA summaries and manifest.
3. Clear separation of implemented versus experimental outputs.

### Risk 5: Scope creep before core reliability is proven

Impact: medium
Mitigation:
1. Stage-gated roadmap.
2. No strategist-layer expansion until Champions core QA is stable.

## 7) 12-Month Phased Plan

### Phase 1 (Months 1-3): Champions Core Reliability

Delivery focus:
1. Source ownership catalog and config-driven controls.
2. Legal pool output and crosswalk mappings.
3. Extended QA, drift checks, release manifest.

Success signals:
1. Stable repeatable runs.
2. High canonical-to-Champions coverage.
3. Publish-ready manifests with zero critical QA failures.

### Phase 2 (Months 4-6): Competitive Context Expansion

Delivery focus:
1. Speed tier and item restriction tables.
2. Tournament and usage metadata ingestion.
3. Schema dictionary and starter analysis pack.

Success signals:
1. Analysts can answer core prep questions from one dataset.
2. Refresh cycle remains within reliability and runtime targets.

### Phase 3 (Months 7-12): Decision-Support Layer

Delivery focus:
1. Opponent-six input contract.
2. Matchup feature views.
3. Gameplan output artifact and evaluation harness.

Success signals:
1. Complete output payload for test scenarios.
2. Evidence traceability from recommendation to source tables.
3. User trust and repeat usage growth.

## 8) Recommendation

Proceed with implementation starting at the near-term Champions core scope. The repository already contains the technical foundation needed to execute with controlled risk. The projected strategic value is positive under conservative adoption assumptions, and the roadmap allows measured expansion toward strategist-ready outputs without overcommitting early.

Decision requested:
1. Approve Phase 1 and Phase 2 as committed scope.
2. Treat Phase 3 as conditional on reliability and adoption milestones.
3. Track value realization monthly via active users, prep time saved proxy, and QA publish success rate.

## 9) Evidence Base in This Repository

This business case is grounded in the current repository artifacts, including:
1. Product requirements and acceptance criteria in docs/product/champions-dataset-prd.md.
2. Sprintable delivery breakdown in docs/product/champions-dataset-backlog.md.
3. Architecture and runbook flow in docs/engineering/architecture-overview.md.
4. Source landscape and ownership context in DATASET.md.
5. Existing normalization, QA, and pipeline entry scripts under scripts.
6. dbt model test contracts under dbt/models.

These references support feasibility claims, scope boundaries, and risk controls in this report.
