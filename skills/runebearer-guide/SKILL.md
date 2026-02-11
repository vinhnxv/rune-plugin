---
name: runebearer-guide
description: |
  Quick reference for invoking Rune agents correctly.
  Use when spawning agents, getting "agent not found" errors, or selecting review agents.

  <example>
  Context: User wants to know which agents are available
  user: "What review agents does Rune have?"
  assistant: "Loading runebearer-guide for the agent reference table"
  </example>
user-invocable: false
---

# Runebearer Guide

Quick reference for all Rune plugin agents, their roles, and invocation patterns.

## Agent Invocation

All Rune agents are plugin agents. Invoke with the `rune:` namespace prefix:

```
Task rune:review:ward-sentinel("Review these files for security")
Task rune:review:forge-oracle("Check performance bottlenecks")
Task rune:utility:runebinder("Aggregate review findings")
```

**Common mistake:** Using agent name without namespace prefix.

```
# WRONG - agent not found
Task ward-sentinel(...)

# CORRECT - full namespace
Task rune:review:ward-sentinel(...)
```

## Review Agents

10 specialized reviewers that form Runebearer teams:

| Agent | Role | Perspective |
|-------|------|-------------|
| `rune:review:ward-sentinel` | Security review | Vulnerabilities, auth, injection, OWASP, prompt injection |
| `rune:review:forge-oracle` | Performance review | Bottlenecks, N+1 queries, async patterns, memory |
| `rune:review:rune-architect` | Architecture review | Layer violations, DDD, dependency direction |
| `rune:review:simplicity-warden` | Simplicity review | YAGNI, over-engineering, premature abstraction |
| `rune:review:flaw-hunter` | Logic review | Edge cases, race conditions, null handling, off-by-one |
| `rune:review:echo-detector` | Duplication review | DRY violations, copy-paste code, similar patterns |
| `rune:review:pattern-seer` | Pattern review | Naming consistency, convention adherence |
| `rune:review:void-analyzer` | Completeness review | Missing error handling, incomplete implementations |
| `rune:review:orphan-finder` | Dead code review | Unused functions, unwired code, orphaned files |
| `rune:review:phantom-checker` | Dynamic reference check | Reflection, string-based imports, meta-programming |

## Runebearer Roles (Consolidated Teammates)

In `/rune:review`, agents are grouped into max 5 Runebearers:

| Runebearer | Agents Embedded | Scope |
|-----------|-----------------|-------|
| **Forge Warden** | rune-architect, forge-oracle, flaw-hunter, echo-detector | Backend code (`.py`, `.go`, `.rs`, `.rb`, `.java`) |
| **Ward Sentinel** | ward-sentinel | ALL files (security always) |
| **Pattern Weaver** | simplicity-warden, pattern-seer, orphan-finder, phantom-checker | ALL files (quality patterns) |
| **Glyph Scribe** | void-analyzer, forge-oracle (frontend) | Frontend code (`.ts`, `.tsx`, `.js`, `.jsx`) |
| **Lore Keeper** | (docs-specific logic) | Docs (`.md` files, conditional) |

## Utility Agents

| Agent | Role |
|-------|------|
| `rune:utility:runebinder` | Aggregates review/audit outputs → writes TOME.md |
| `rune:utility:flow-seer` | Spec flow analysis |
| `rune:utility:scroll-reviewer` | Document quality review |

## Research Agents

| Agent | Role |
|-------|------|
| `rune:research:lore-seeker` | External best practices research |
| `rune:research:realm-analyst` | Codebase/repo exploration |
| `rune:research:codex-scholar` | Framework documentation research |
| `rune:research:echo-reader` | Reads Rune Echoes (past learnings) |
| `rune:research:chronicle-miner` | Git history archaeology |

## Work Agents

| Agent | Role |
|-------|------|
| `rune:work:rune-smith` | Code implementation (TDD-aware) |
| `rune:work:trial-forger` | Test generation |

## Runebearer Selection Logic

The `/rune:review` command selects Runebearers based on file extensions (Rune Gaze):

| File Pattern | Runebearers Selected |
|-------------|---------------------|
| `**/*.py` | Forge Warden + Ward Sentinel + Pattern Weaver |
| `**/*.{ts,tsx,js,jsx}` | Glyph Scribe + Ward Sentinel + Pattern Weaver |
| `**/*.md` (>= 10 lines changed) | Lore Keeper (conditional) |
| Mixed code + docs | All applicable Runebearers |

Ward Sentinel and Pattern Weaver are ALWAYS selected regardless of file types.

See `rune-circle` skill for full Runebearer architecture and prompts.
