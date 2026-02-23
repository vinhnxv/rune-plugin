# Roundtable Circle — Creation Log

## Problem Statement
Code review with a single agent missed perspective diversity — a security specialist wouldn't catch performance issues, and a performance analyst wouldn't catch naming inconsistencies. Ad-hoc review also suffered from context overflow when one large agent tried to hold the entire diff in memory. Reviews were either shallow (single pass) or expensive (manual agent selection by the user).

## Alternatives Considered
| Alternative | Why Rejected |
|-------------|--------------|
| Single large agent with all review knowledge | Context overflow — a single agent cannot hold 23 review perspectives plus the full diff in one 200k window. Quality degrades as context fills. |
| Sequential review (one agent after another) | Too slow — 7 agents running sequentially at 2-3 minutes each = 15-20 minutes. Parallel execution cuts this to 3-5 minutes. |
| Manual agent selection by user | User burden — requires knowledge of which agents exist and which are relevant to the current diff. Rune Gaze automates this via file extension classification. |
| Unstructured parallel agents | No aggregation — agents would produce 7 separate reports with duplicate findings. The Runebinder aggregation phase (Phase 5) deduplicates by priority hierarchy. |

## Key Design Decisions
- **7-phase lifecycle (Rune Gaze → Forge Team → Summon Ash → Monitor → Aggregate → Verify → Cleanup)**: Each phase has a clear contract and failure mode. Removing any phase creates a gap (e.g., skipping Monitor means no stale detection, skipping Aggregate means duplicate findings).
- **Inscription-based contracts (inscription.json)**: Each Ash receives its file assignment, diff scope, and output path via a structured JSON contract — not embedded in the prompt. This prevents prompt bloat and enables deterministic file routing.
- **TOME aggregation with priority hierarchy (SEC > BACK > VEIL > DOUBT > DOC > QUAL > FRONT > CDX)**: When two Ashes flag the same issue, the higher-priority prefix wins. This prevents duplicate findings in the resolution report without losing coverage.
- **Seal-based completion detection**: Each Ash emits a `<seal>` marker as the last line of output. The TeammateIdle hook validates seal presence before allowing the agent to go idle. This catches silent crashes (agent stops without reporting).

## Observed Rationalizations (from Skill Testing)
Agent behaviors observed during pressure testing:
- "I'll review all the files" (ignoring file assignment) → Counter: Inscription contract restricts each Ash to assigned files only
- "No issues found" (without reading files) → Counter: Inner Flame Layer 1 requires evidence of Read() calls

## Iteration History
| Date | Version | Change | Trigger |
|------|---------|--------|---------|
| 2026-02-08 | v1.0 | Initial 7-phase lifecycle with 7 built-in Ashes | Ad-hoc single-agent reviews missing perspective diversity |
| 2026-02-13 | v1.1 | Added Forge Gaze topic-aware agent selection | Users getting irrelevant agents for their diff type |
| 2026-02-18 | v1.2 | Added Doubt Seer adversarial verification (Phase 4.5) | False positive findings wasting mend cycles |
| 2026-02-21 | v1.3 | Added multi-wave deep review (--deep flag) | Audit-depth analysis needed without separate audit command |
| 2026-02-23 | v1.4 | CLI-backed Ashes support for external models | Users wanting cross-model review perspectives |
