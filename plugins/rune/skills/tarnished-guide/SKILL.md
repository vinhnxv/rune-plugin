---
name: tarnished-guide
description: |
  Provides a quick reference for invoking Rune agents correctly.
  This skill should be used when spawning agents, troubleshooting "agent not found" errors, or selecting review agents.

  <example>
  Context: User wants to know which agents are available
  user: "What review agents does Rune have?"
  assistant: "Loading tarnished-guide for the agent reference table"
  </example>
user-invocable: false
allowed-tools:
  - Read
  - Glob
---

# Tarnished Guide

Quick reference for all Rune plugin agents, their roles, and invocation patterns.

## Agent Invocation

All Rune agents are plugin agents. Invoke with the `rune:` namespace prefix:

```
Task rune:review:ward-sentinel("Review these files for security")
Task rune:review:ember-oracle("Check performance bottlenecks")
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

10 specialized reviewers that form Tarnished teams:

| Agent | Role | Perspective |
|-------|------|-------------|
| `rune:review:ward-sentinel` | Security review | Vulnerabilities, auth, injection, OWASP, prompt injection |
| `rune:review:ember-oracle` | Performance review | Bottlenecks, N+1 queries, async patterns, memory |
| `rune:review:rune-architect` | Architecture review | Layer violations, DDD, dependency direction |
| `rune:review:simplicity-warden` | Simplicity review | YAGNI, over-engineering, premature abstraction |
| `rune:review:flaw-hunter` | Logic review | Edge cases, race conditions, null handling, off-by-one |
| `rune:review:mimic-detector` | Duplication review | DRY violations, copy-paste code, similar patterns |
| `rune:review:pattern-seer` | Pattern review | Naming consistency, convention adherence |
| `rune:review:void-analyzer` | Completeness review | Missing error handling, incomplete implementations |
| `rune:review:wraith-finder` | Dead code review | Unused functions, unwired code, orphaned files |
| `rune:review:phantom-checker` | Dynamic reference check | Reflection, string-based imports, meta-programming |

## Tarnished Roles (Consolidated Teammates)

In `/rune:review`, agents are grouped into max 5 Tarnished:

| Tarnished | Agents Embedded | Scope |
|-----------|-----------------|-------|
| **Forge Warden** | rune-architect, ember-oracle, flaw-hunter, mimic-detector | Backend code (`.py`, `.go`, `.rs`, `.rb`, `.java`) |
| **Ward Sentinel** | ward-sentinel | ALL files (security always) |
| **Pattern Weaver** | simplicity-warden, pattern-seer, wraith-finder, phantom-checker, void-analyzer | ALL files (quality patterns) |
| **Glyph Scribe** | Inline perspectives (TypeScript safety, React performance, accessibility) | Frontend code (`.ts`, `.tsx`, `.js`, `.jsx`) |
| **Knowledge Keeper** | Inline perspectives (accuracy, completeness, consistency) | Docs (`.md` files, conditional) |

**Note:** Forge Warden, Ward Sentinel, and Pattern Weaver embed dedicated review agent files. Glyph Scribe and Knowledge Keeper use inline perspective definitions in their Tarnished prompts (no dedicated agent files).

## Utility Agents

| Agent | Role |
|-------|------|
| `rune:utility:runebinder` | Aggregates review/audit outputs → writes TOME.md |
| `rune:utility:truthseer-validator` | Audit coverage validation (Phase 5.5) |
| `rune:utility:flow-seer` | Spec flow analysis |
| `rune:utility:scroll-reviewer` | Document quality review |
| `rune:utility:decree-arbiter` | Technical soundness review for plans |
| `rune:utility:mend-fixer` | Parallel code fixer for /rune:mend findings |
| `rune:utility:knowledge-keeper` | Documentation coverage reviewer for plans |

## Research Agents

| Agent | Role |
|-------|------|
| `rune:research:practice-seeker` | External best practices research |
| `rune:research:repo-surveyor` | Codebase/repo exploration |
| `rune:research:lore-scholar` | Framework documentation research |
| `rune:research:echo-reader` | Reads Rune Echoes (past learnings) |
| `rune:research:git-miner` | Git history archaeology |

## Work Agents

| Agent | Role |
|-------|------|
| `rune:work:rune-smith` | Code implementation (TDD-aware) |
| `rune:work:trial-forger` | Test generation |

## Tarnished Selection Logic

The `/rune:review` command selects Tarnished based on file extensions (Rune Gaze):

| File Pattern | Tarnished Selected |
|-------------|---------------------|
| `**/*.py` | Forge Warden + Ward Sentinel + Pattern Weaver |
| `**/*.{ts,tsx,js,jsx}` | Glyph Scribe + Ward Sentinel + Pattern Weaver |
| `**/*.md` (>= 10 lines changed) | Knowledge Keeper (conditional) |
| Mixed code + docs | All applicable Tarnished |

Ward Sentinel and Pattern Weaver are ALWAYS selected regardless of file types.

See `roundtable-circle` skill for full Tarnished architecture and prompts.
