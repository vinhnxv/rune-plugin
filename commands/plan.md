---
name: plan
description: |
  Multi-agent planning workflow using Agent Teams. Combines brainstorm, research,
  synthesis, deepening, and review into a single orchestrated pipeline with
  dependency-aware task scheduling.

  <example>
  user: "/rune:plan"
  assistant: "Starting Rune planning workflow with parallel research agents..."
  </example>

  <example>
  user: "/rune:plan --brainstorm --deep"
  assistant: "Starting full planning pipeline with brainstorm and deep research..."
  </example>
user-invocable: true
allowed-tools:
  - Task
  - TaskCreate
  - TaskList
  - TaskUpdate
  - TaskGet
  - TeamCreate
  - TeamDelete
  - SendMessage
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
  - WebSearch
  - WebFetch
---

# /rune:plan — Multi-Agent Planning Workflow

Orchestrates a planning pipeline using Agent Teams with dependency-aware task scheduling.

## Usage

```
/rune:plan                      # Standard planning (research + synthesize + review)
/rune:plan --brainstorm         # Start with brainstorm phase
/rune:plan --deep               # Include deep research phase
/rune:plan --brainstorm --deep  # Full pipeline
```

## Pipeline Overview

```
Phase 0: Gather Input (brainstorm or accept description)
    ↓
Phase 1: Research (3-5 parallel agents)
    ↓ (all research tasks converge)
Phase 2: Synthesize (lead consolidates findings)
    ↓
Phase 3: Deepen (optional, parallel section-level research)
    ↓
Phase 4: Scroll Review (document quality check)
    ↓
Phase 5: Echo Persist (save learnings)
    ↓
Output: plans/{type}-{name}-plan.md
```

## Phase 0: Gather Input

### Without `--brainstorm`

Ask the user for a feature description:

```javascript
AskUserQuestion({
  questions: [{
    question: "What would you like to plan?",
    header: "Feature",
    options: [
      { label: "New feature", description: "Add new functionality" },
      { label: "Bug fix", description: "Fix an existing issue" },
      { label: "Refactor", description: "Improve existing code" }
    ],
    multiSelect: false
  }]
})
```

Then ask for details. Collect until the feature is clear.

### With `--brainstorm`

Run an interactive brainstorm session:
1. Ask 3-5 questions one at a time using AskUserQuestion
2. Explore 2-3 approaches, recommend one
3. Capture decisions for research phase

## Phase 1: Research (Parallel)

Create an Agent Teams team and spawn parallel research tasks.

```javascript
// 1. Create team
TeamCreate({ team_name: "rune-plan-{timestamp}" })

// 2. Create research output directory
mkdir -p tmp/plans/{timestamp}/research/

// 3. Create parallel tasks (no dependencies)
TaskCreate({ subject: "Research best practices", description: "..." })      // #1
TaskCreate({ subject: "Research repo patterns", description: "..." })       // #2
TaskCreate({ subject: "Research framework docs", description: "..." })      // #3
TaskCreate({ subject: "Read past echoes", description: "..." })             // #4

// 4. Spawn research agents
Task({
  team_name: "rune-plan-{timestamp}",
  name: "lore-seeker",
  subagent_type: "general-purpose",
  prompt: `You are Lore Seeker. Research best practices for: {feature}.
    Write findings to tmp/plans/{timestamp}/research/best-practices.md.
    Claim task #1 via TaskList/TaskUpdate.
    See agents/research/lore-seeker.md for full instructions.`,
  run_in_background: true
})

Task({
  team_name: "rune-plan-{timestamp}",
  name: "realm-analyst",
  subagent_type: "general-purpose",
  prompt: `You are Realm Analyst. Explore the codebase for: {feature}.
    Write findings to tmp/plans/{timestamp}/research/repo-analysis.md.
    Claim task #2 via TaskList/TaskUpdate.
    See agents/research/realm-analyst.md for full instructions.`,
  run_in_background: true
})

Task({
  team_name: "rune-plan-{timestamp}",
  name: "codex-scholar",
  subagent_type: "general-purpose",
  prompt: `You are Codex Scholar. Research framework docs for: {feature}.
    Write findings to tmp/plans/{timestamp}/research/framework-docs.md.
    Claim task #3 via TaskList/TaskUpdate.
    See agents/research/codex-scholar.md for full instructions.`,
  run_in_background: true
})

Task({
  team_name: "rune-plan-{timestamp}",
  name: "echo-reader",
  subagent_type: "general-purpose",
  prompt: `You are Echo Reader. Read .claude/echoes/ for relevant past learnings.
    Write findings to tmp/plans/{timestamp}/research/past-echoes.md.
    Claim task #4 via TaskList/TaskUpdate.
    See agents/research/echo-reader.md for full instructions.`,
  run_in_background: true
})
```

### Monitor Research

Poll TaskList every 30 seconds until all 4 research tasks are completed.

```javascript
while (not all research tasks completed):
  tasks = TaskList()
  if (all 4 completed): break
  if (any stale > 5 min): proceed with partial
  sleep(30)
```

## Phase 2: Synthesize

After research completes, the lead consolidates findings:

1. Read all research output files from `tmp/plans/{timestamp}/research/`
2. Identify common themes, conflicting advice, key patterns
3. Draft the plan document with sections:

```markdown
---
title: "{type}: {feature description}"
type: feat | fix | refactor
date: YYYY-MM-DD
---

# {Feature Title}

## Overview
{What and why}

## Proposed Solution
{High-level approach informed by research}

## Technical Approach
{Implementation details referencing codebase patterns}

## Acceptance Criteria
- [ ] {Testable requirement}

## References
- {Research findings links}
```

4. Write to `plans/{type}-{feature-name}-plan.md`

## Phase 3: Deepen (Optional — `--deep` flag)

If `--deep` is specified, spawn additional agents to enhance each plan section:

```javascript
// Create deepen tasks blocked by synthesis
TaskCreate({ subject: "Deepen: {section 1}" })     // #5
TaskCreate({ subject: "Deepen: {section 2}" })     // #6
// ... one per major section

// Each deepen task gets its own research agent
Task({
  team_name: "rune-plan-{timestamp}",
  name: "deep-researcher-{n}",
  subagent_type: "general-purpose",
  prompt: `Research specific best practices for: {section topic}.
    Write enhancements to tmp/plans/{timestamp}/deepen/{section}.md`,
  run_in_background: true
})
```

After deepen completes, merge enhancements into the plan document.

## Phase 4: Scroll Review

Spawn a document quality reviewer:

```javascript
Task({
  team_name: "rune-plan-{timestamp}",
  name: "scroll-reviewer",
  subagent_type: "general-purpose",
  prompt: `You are Scroll Reviewer. Review the plan at plans/{type}-{name}-plan.md.
    Write review to tmp/plans/{timestamp}/scroll-review.md.
    See agents/utility/scroll-reviewer.md for quality criteria.`,
  run_in_background: true
})
```

If the review identifies HIGH severity issues, address them before proceeding.

## Phase 5: Echo Persist

Persist planning learnings to Rune Echoes:

```javascript
if (exists(".claude/echoes/planner/")) {
  // Write architectural discoveries and patterns found during research
  appendEchoEntry("echoes/planner/MEMORY.md", {
    layer: "inscribed",
    source: `rune:plan ${timestamp}`,
    // ... key learnings from this planning session
  })
}
```

## Phase 6: Cleanup & Present

```javascript
// 1. Shutdown all teammates
for (const teammate of allTeammates) {
  SendMessage({ type: "shutdown_request", recipient: teammate })
}

// 2. Wait for approvals (max 30s)

// 3. Cleanup team
TeamDelete()

// 4. Present plan to user
Read("plans/{type}-{feature-name}-plan.md")
```

## Output

Plan file written to: `plans/{type}-{feature-name}-plan.md`

After presenting the plan, offer next steps:

```
Plan ready at plans/{type}-{name}-plan.md

Next steps:
1. /rune:work — Start implementing this plan
2. Edit plan — Refine before implementing
3. /rune:review — Review the plan document
```

## Error Handling

| Error | Recovery |
|-------|----------|
| Research agent timeout (>5 min) | Proceed with partial research |
| No git history (chronicle-miner) | Skip, report gap |
| No echoes (echo-reader) | Skip, proceed without history |
| Scroll review finds critical gaps | Address before presenting |
