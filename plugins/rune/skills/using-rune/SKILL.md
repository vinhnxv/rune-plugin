---
name: using-rune
description: |
  Use when the user asks to review code, plan features, audit a codebase,
  implement a plan, fix review findings, debug failed builds, analyze code
  impact, or run end-to-end workflows. Also use when the user seems unsure
  which Rune command to use, when the user says "review", "plan", "audit",
  "implement", "fix findings", "ship it", "check my code", "what changed",
  or "help me think through this". Routes user intent to the correct
  /rune:* command. Keywords: which command, what to use, rune help, workflow
  routing, review, audit, plan, implement.
user-invocable: false
disable-model-invocation: false
---

# Using Rune — Workflow Discovery & Routing

When a user's request matches a Rune workflow, **suggest the appropriate command before responding**.
Do not auto-invoke heavyweight commands — suggest and let the user confirm.

## Intent Routing Table

| User Says | Suggest | Why |
|-----------|---------|-----|
| "Review my code" / "check this PR" / "code review" | `/rune:appraise` | Multi-agent review of changed files |
| "Audit the codebase" / "security scan" / "full review" | `/rune:audit` | Comprehensive codebase analysis (all files, not just diff) |
| "Plan a feature" / "design this" / "how should we build" | `/rune:devise` | Multi-agent planning pipeline (brainstorm + research + synthesize) |
| "Quick plan" / "just outline it" | `/rune:devise --quick` | Lightweight planning (research + synthesize, skip brainstorm/forge) |
| "Implement this" / "build it" / "execute the plan" | `/rune:strive plans/...` | Swarm workers execute a plan file |
| "Fix these findings" / "resolve the review" | `/rune:mend tmp/.../TOME.md` | Parallel resolution of review findings |
| "Run everything" / "ship it" / "end to end" | `/rune:arc plans/...` | Full 18-phase pipeline (forge → work → review → mend → test → goldmask → ship → merge) |
| "Batch arc" / "run all plans" / "overnight" / "multiple plans" | `/rune:arc-batch plans/*.md` | Sequential batch arc execution with auto-merge and crash recovery |
| "Process GitHub issues" / "run issues" / "issue backlog" / "auto-implement from issues" | `/rune:arc-issues --label "rune:ready"` | GitHub Issues-driven batch arc — fetches issues, generates plans, runs arc, comments results |
| "Deepen this plan" / "add more detail" / "enrich" | `/rune:forge plans/...` | Forge Gaze topic-aware enrichment |
| "What changed?" / "blast radius" / "impact analysis" | `/rune:goldmask` | Cross-layer impact analysis (Impact + Wisdom + Lore) |
| "Help me think through" / "structured reasoning" | `/rune:elicit` | Interactive elicitation method selection |
| "Clean up" / "remove temp files" | `/rune:rest` | Remove tmp/ artifacts from completed workflows |
| "Cancel the review" / "stop the audit" | `/rune:cancel-review` or `/rune:cancel-audit` | Graceful shutdown of active workflows |

### Beginner Aliases

For users new to Rune, these simpler commands forward to the full versions:

| User Says | Suggest | Equivalent |
|-----------|---------|------------|
| "plan" / "plan this" | `/rune:plan` | `/rune:devise` |
| "work" / "build" / "implement" | `/rune:work` | `/rune:strive` |
| "review" / "check my code" | `/rune:review` | `/rune:appraise` |

## Routing Rules

1. **Suggest, don't auto-invoke.** Rune commands spawn agent teams. Always confirm first.
2. **One command per intent.** If ambiguous, ask which workflow they want.
3. **Check for prerequisites.** `/rune:strive` needs a plan file. `/rune:mend` needs a TOME. `/rune:arc` needs a plan.
4. **Recent artifacts matter.** Check `plans/` for recent plans, `tmp/reviews/` for recent TOMEs.

## When NOT to Route

- Simple questions about the codebase → answer directly
- Single-file edits → edit directly
- Git operations → use git directly
- Questions about Rune itself → use `ash-guide` skill

## Quick Reference: Command Capabilities

| Command | Spawns Agents? | Duration | Input Required |
|---------|---------------|----------|----------------|
| `/rune:appraise` | Yes (up to 8) | 3-10 min | Git diff (auto-detected) |
| `/rune:audit` | Yes (up to 8) | 5-15 min | None (scans all files) |
| `/rune:devise` | Yes (up to 7) | 5-15 min | Feature description |
| `/rune:strive` | Yes (swarm) | 10-30 min | Plan file path |
| `/rune:mend` | Yes (per file) | 3-10 min | TOME file path |
| `/rune:arc` | Yes (per phase) | 30-90 min | Plan file path |
| `/rune:arc-batch` | Yes (per plan) | 45-240 min/plan | Plan glob or queue file |
| `/rune:arc-issues` | Yes (per issue) | 45-240 min/issue | GitHub issue labels or numbers |
| `/rune:forge` | Yes (per section) | 5-15 min | Plan file path |
| `/rune:goldmask` | Yes (8 tracers) | 5-10 min | Diff spec or file list |
| `/rune:elicit` | No | 2-5 min | Topic |
| `/rune:rest` | No | <1 min | None |
| `/rune:plan` | (alias for `/rune:devise`) |||
| `/rune:work` | (alias for `/rune:strive`) |||
| `/rune:review` | (alias for `/rune:appraise`) |||
