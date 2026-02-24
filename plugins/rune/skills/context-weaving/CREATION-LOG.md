# Context Weaving — Creation Log

## Problem Statement
Agent teams consuming the orchestrator's entire context window, causing quality degradation in later phases. With 4+ agents reporting verbose findings back to the orchestrator, the context would fill up by Phase 6 (code review), leaving insufficient room for Phase 7 (mend) and beyond. The orchestrator's instructions would get compacted away, leading to drift in agent coordination and missed protocol steps.

## Alternatives Considered
| Alternative | Why Rejected |
|-------------|--------------|
| Smaller agent teams (2-3 agents) | Loses perspective diversity — the whole point of multi-agent review is covering security, performance, patterns, and correctness simultaneously. Reducing to 2 agents defeats the purpose. |
| Larger context windows | Even with larger windows, the fundamental problem remains — verbose agent output scales linearly while orchestrator instructions are fixed-size. |
| Manual pruning by orchestrator | Unreliable — the orchestrator LLM inconsistently decides what to prune. Critical protocol steps get dropped while verbose agent output is preserved. |
| File-based output only (no inline) | Partially adopted (Agent Teams give each teammate its own context window), but the orchestrator still needs to read summaries. Context weaving manages the residual overflow from summary reads. |

## Key Design Decisions
- **Unified overflow/rot/compression/offloading model**: Four separate mechanisms (pre-spawn overflow check, stale context rot detection, long-session compression, verbose content offloading) are unified into a single skill. Previously these were scattered across multiple skill files, leading to inconsistent application.
- **Glyph budget system**: Each phase gets a token budget for how much artifact content the orchestrator should read inline. Exceeding the budget triggers offloading to filesystem with a summary pointer. This prevents any single phase from consuming disproportionate context.
- **Pre-spawn context checks**: Before summoning agents, verify available context is sufficient. If insufficient, compress or offload before spawning. This prevents the worst failure mode — spawning agents that produce output the orchestrator can't process.

## Observed Rationalizations (from Skill Testing)
Agent behaviors observed during pressure testing:
- "I'll read the full TOME inline" (instead of reading the summary header) → Counter: Glyph budget enforces summary-only reads for artifacts exceeding budget
- "Context seems fine" (ignoring token count) → Counter: Pre-spawn check is deterministic, not a judgment call

## Iteration History
| Date | Version | Change | Trigger |
|------|---------|--------|---------|
| 2026-02-10 | v1.0 | Initial unified context management (overflow + rot + compression + offloading) | Orchestrator context overflow after 2 phases with 4+ agents |
| 2026-02-15 | v1.1 | Tuned trigger threshold (4+ agents, 50 messages) | False positives on small sessions; false negatives on agent-heavy sessions |
| 2026-02-20 | v1.2 | Simplified strategy tiers from 3 to 2 | Over-engineering — 3 tiers added complexity without improving outcomes |
