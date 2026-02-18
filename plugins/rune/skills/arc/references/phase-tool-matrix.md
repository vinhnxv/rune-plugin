# Per-Phase Tool Restrictions (F8)

The arc orchestrator passes only phase-appropriate tools when creating each phase's team.

| Phase | Tools | Rationale |
|-------|-------|-----------|
| Phase 1 (FORGE) | Delegated to `/rune:forge` (read-only agents + Edit for enrichment merge). Codex Oracle (if detected) additionally requires Bash for `codex exec` | Enrichment only, no codebase modification |
| Phase 2 (PLAN REVIEW) | Read, Glob, Grep, Write (own output file only) | Review -- no codebase modification |
| Phase 2.5 (PLAN REFINEMENT) | Read, Write, Glob, Grep | Orchestrator-only -- extraction, no team |
| Phase 2.7 (VERIFICATION) | Read, Glob, Grep, Write, Bash (git history) | Orchestrator-only -- deterministic checks |
| Phase 5 (WORK) | Full access (Read, Write, Edit, Bash, Glob, Grep) | Implementation requires all tools |
| Phase 5.5 (GAP ANALYSIS) | Read, Glob, Grep, Bash (git diff, grep) | Orchestrator-only -- deterministic cross-reference |
| Phase 6 (CODE REVIEW) | Read, Glob, Grep, Write (own output file only). Codex Oracle (if detected) additionally requires Bash for `codex exec` | Review -- no codebase modification |
| Phase 7 (MEND) | Orchestrator: full. Fixers: restricted (see mend-fixer) | Least privilege for fixers |
| Phase 7.5 (VERIFY MEND) | Read, Glob, Grep, Write, Bash (git diff) | Orchestrator-only — convergence controller (no team) |
| Phase 8 (AUDIT) | Read, Glob, Grep, Write (own output file only). Codex Oracle (if detected) additionally requires Bash for `codex exec` | Audit -- no codebase modification |

Worker and fixer agent prompts include: "Do not modify files in `.claude/arc/`". Only the arc orchestrator writes to checkpoint.json.

## Time Budget per Phase

| Phase | Timeout | Notes |
|-------|---------|-------|
| FORGE | 15 min | Inner 10m + 5m setup budget |
| PLAN REVIEW | 15 min | Inner 10m + 5m setup budget |
| PLAN REFINEMENT | 3 min | Orchestrator-only, no agents |
| VERIFICATION | 30 sec | Deterministic checks, no LLM |
| WORK | 35 min | Inner 30m + 5m setup budget |
| GAP ANALYSIS | 1 min | Orchestrator-only, deterministic text checks |
| CODE REVIEW | 15 min | Inner 10m + 5m setup budget |
| MEND | 23 min | Inner 15m + 5m setup + 3m ward/cross-file |
| VERIFY MEND | 4 min | Convergence evaluation (orchestrator-only); re-review cycles run as separate Phase 6+7 |
| AUDIT | 20 min | Inner 15m + 5m setup budget |

**Total pipeline hard ceiling**: Dynamic (162-240 min based on tier; hard cap 240 min). See `calculateDynamicTimeout()` in SKILL.md.

Delegated phases use inner-timeout + 60s buffer so the delegated command handles its own timeout first; the arc timeout is a safety net only.
