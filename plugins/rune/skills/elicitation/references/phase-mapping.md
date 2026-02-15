# Phase Mapping — Elicitation Methods

Maps each elicitation method to its target Rune phases, specifying when and how methods are injected.

## Phase Overview

> Counts derived from methods.csv. Re-verify after CSV changes.

| Phase | Command | Methods Available | Auto-Suggest |
|-------|---------|------------------|--------------|
| Plan Phase 0 (Brainstorm) | `/rune:plan` | 6 | 5 Tier 1, 1 Tier 2 |
| Plan Phase 1 (Research) | `/rune:plan` | 1 | 1 Tier 1 |
| Plan Phase 1.8 (Solution Arena) | `/rune:plan` | 4 | 4 Tier 1 |
| Plan Phase 2 (Synthesize) | `/rune:plan` | 2 | 1 Tier 1, 1 Tier 2 |
| Plan Phase 2.5 (Shatter) | `/rune:plan` | 2 | 1 Tier 1, 1 Tier 2 |
| Plan Phase 4 (Review) | `/rune:plan` | 3 | 3 Tier 1 |
| Forge Phase 3 | `/rune:forge` | 7 | 5 Tier 1, 2 Tier 2 |
| Work Phase 5 | `/rune:work` | 3 | 3 Tier 1 |
| Arc Phase 5.5 (Gap Analysis) | `/rune:arc` | 1 | 1 Tier 1 |
| Review Phase 6 | `/rune:review` | 6 | 3 Tier 1, 3 Tier 2 |
| Arc Phase 7 (Mend) | `/rune:arc` | 1 | 1 Tier 1 |
| Arc Phase 7.5 (Verify Mend) | `/rune:arc` | 2 | 2 Tier 1 |
| Arc Phase 8 (Audit) | `/rune:arc` | 3 | 1 Tier 1, 2 Tier 2 |

## Detailed Phase Mappings

### Plan Phase 0 — Brainstorm

**Integration point**: After approach selection in `commands/plan.md`
**Injection type**: AskUserQuestion-based method selection

| Method | Tier | When Auto-Suggested |
|--------|------|-------------------|
| Stakeholder Round Table | 1 | Feature affects multiple user types |
| Debate Club Showdown | 1 | 2+ viable approaches with trade-offs |
| Cross-Functional War Room | 1 | Feature has eng/design/product tensions |
| Mentor and Apprentice | 1 | Complex domain, hidden assumptions |
| First Principles Analysis | 1 | Novel feature, no clear precedent |
| User Persona Focus Group | 2 | UX-facing features (manual selection only) |

### Plan Phase 1.8 — Solution Arena

**Integration point**: After solution generation in `solution-arena.md`
**Injection type**: Structured evaluation templates for challenger agents

| Method | Tier | When Auto-Suggested |
|--------|------|-------------------|
| Tree of Thoughts | 1 | Multiple solution paths need structured evaluation |
| Comparative Analysis Matrix | 1 | Weighted scoring across evaluation dimensions |
| Pre-mortem Analysis | 1 | Devil's Advocate failure scenario generation |
| Architecture Decision Records | 1 | Trade-off documentation for solution selection rationale |

### Forge Phase 3 — Enrichment

**Integration point**: Forge Gaze topic registry in `forge-gaze.md`
**Injection type**: Prompt modifier appended to matched agent's prompt

| Method | Tier | Preferred Agent |
|--------|------|----------------|
| Tree of Thoughts | 1 | decree-arbiter |
| Architecture Decision Records | 1 | decree-arbiter, rune-architect |
| Comparative Analysis Matrix | 1 | any matched agent |
| First Principles Analysis | 1 | any matched agent |
| Debate Club Showdown | 1 | any matched agent |
| Good Cop Bad Cop | 2 | any matched agent |
| Occam's Razor Application | 2 | simplicity-warden |

### Work Phase 5 — Implementation

**Integration point**: Worker task prompts during `/rune:work` execution
**Injection type**: 2-3 line additions to worker task description

| Method | Tier | When Injected |
|--------|------|--------------|
| Tree of Thoughts | 1 | Complex architecture/design tasks |
| Mentor and Apprentice | 1 | Domain-complex tasks |
| 5 Whys Deep Dive | 1 | Bug fix / root-cause tasks |

### Arc Phase 5.5 — Gap Analysis

**Integration point**: Orchestrator context when gap analysis reveals MISSING criteria
**Injection type**: Structured reasoning prompt for addressing gaps

| Method | Tier | When Auto-Suggested |
|--------|------|-------------------|
| Pre-mortem Analysis | 1 | Gap analysis reveals MISSING acceptance criteria |

### Review Phase 6 — Code Review

**Integration point**: Ash agent prompts during Roundtable Circle
**Injection type**: Additional review dimensions in agent prompt

| Method | Tier | Target Agent |
|--------|------|-------------|
| Red Team vs Blue Team | 1 | ward-sentinel |
| Challenge from Critical Perspective | 1 | scroll-reviewer |
| Critique and Refine | 1 | scroll-reviewer |
| Code Review Gauntlet | 2 | any Ash |
| Security Audit Personas | 2 | ward-sentinel |
| Occam's Razor Application | 2 | simplicity-warden |

### Arc Phase 7 — Mend

**Integration point**: mend-fixer agent prompt
**Injection type**: Root cause protocol step (5 Whys)

| Method | Tier | Trigger Condition |
|--------|------|------------------|
| 5 Whys Deep Dive | 1 | P1 severity OR 3+ recurring findings |

### Arc Phase 7.5 — Verify Mend

**Integration point**: Spot-check reviewer context
**Injection type**: Verification dimensions

| Method | Tier | Application |
|--------|------|------------|
| Self-Consistency Validation | 1 | Cross-check fix consistency |
| Critique and Refine | 1 | Systematic fix quality assessment |

### Arc Phase 8 — Audit

**Integration point**: Audit Ash agent prompts
**Injection type**: Additional audit dimensions

| Method | Tier | Target Agent |
|--------|------|-------------|
| Red Team vs Blue Team | 1 | ward-sentinel |
| Security Audit Personas | 2 | ward-sentinel |
| Chaos Monkey Scenarios | 2 | flaw-hunter |
