---
name: rune:plan
description: |
  Multi-agent planning workflow using Agent Teams. Combines brainstorm, research,
  synthesis, deepening, and review into a single orchestrated pipeline with
  dependency-aware task scheduling.

  <example>
  user: "/rune:plan"
  assistant: "Starting Rune planning workflow with parallel research agents..."
  </example>

  <example>
  user: "/rune:plan --brainstorm --forge"
  assistant: "Starting full planning pipeline with brainstorm and research enrichment..."
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
/rune:plan                              # Standard planning (research + synthesize + review)
/rune:plan --brainstorm                 # Start with brainstorm phase
/rune:plan --forge                      # Include research enrichment (replaces --deep)
/rune:plan --forge --exhaustive         # Spawn ALL agents per section
/rune:plan --brainstorm --forge         # Full pipeline
```

## Pipeline Overview

```
Phase 0: Gather Input (brainstorm auto-detect or accept description)
    ↓
Phase 1: Research (up to 6 parallel agents, conditional)
    ├─ Phase 1A: LOCAL RESEARCH (always — repo-surveyor, echo-reader, git-miner)
    ├─ Phase 1B: RESEARCH DECISION (risk + local sufficiency scoring)
    ├─ Phase 1C: EXTERNAL RESEARCH (conditional — practice-seeker, codex-scholar)
    └─ Phase 1D: SPEC VALIDATION (always — flow-seer)
    ↓ (all research tasks converge)
Phase 2: Synthesize (lead consolidates findings, detail level selection)
    ↓
Phase 3: Forge (optional — --forge flag, structured deepen per section)
    ↓
Phase 4: Scroll Review (document quality check)
    ↓
Phase 5: Echo Persist (save learnings)
    ↓
Output: plans/{type}-{name}-plan.md
```

## Phase 0: Gather Input

### Brainstorm Auto-Detection

Before asking for input, check for recent brainstorms that match:

```javascript
// Search for recent brainstorms matching the feature
const brainstorms = Glob("docs/brainstorms/*.md")
// Filter: created within last 14 days, topic matches feature
// If found: read and use as input, skip Phase 0 questioning
// If multiple match: AskUserQuestion to select
// If none: proceed with normal Phase 0 flow
```

**Matching thresholds**:
- Auto-use (>= 0.85): Exact/fuzzy title match or strong tag overlap (>= 2 tags)
- Ask user (0.70-0.85): Single semantic match, show with confirmation
- Skip (< 0.70): No relevant brainstorm found

**Recency decay**: >14 days: 0.7x, >30 days: 0.4x, >90 days: skip.

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

## Phase 1: Research (Conditional, up to 6 agents)

Create an Agent Teams team and spawn research tasks using the conditional research pipeline.

### Phase 1A: Local Research (always runs)

```javascript
// 1. Create team
TeamCreate({ team_name: "rune-plan-{timestamp}" })

// 2. Create research output directory
mkdir -p tmp/plans/{timestamp}/research/

// 3. Spawn local research agents (always run — these are cheap and essential)
TaskCreate({ subject: "Research repo patterns", description: "..." })       // #1
TaskCreate({ subject: "Read past echoes", description: "..." })             // #2
TaskCreate({ subject: "Analyze git history", description: "..." })          // #3

Task({
  team_name: "rune-plan-{timestamp}",
  name: "repo-surveyor",
  subagent_type: "general-purpose",
  prompt: `You are Repo Surveyor. Explore the codebase for: {feature}.
    Write findings to tmp/plans/{timestamp}/research/repo-analysis.md.
    Claim task #1 via TaskList/TaskUpdate.
    See agents/research/repo-surveyor.md for full instructions.`,
  run_in_background: true
})

Task({
  team_name: "rune-plan-{timestamp}",
  name: "echo-reader",
  subagent_type: "general-purpose",
  prompt: `You are Echo Reader. Read .claude/echoes/ for relevant past learnings.
    Write findings to tmp/plans/{timestamp}/research/past-echoes.md.
    Claim task #2 via TaskList/TaskUpdate.
    See agents/research/echo-reader.md for full instructions.`,
  run_in_background: true
})

Task({
  team_name: "rune-plan-{timestamp}",
  name: "git-miner",
  subagent_type: "general-purpose",
  prompt: `You are Git Miner. Analyze git history for: {feature}.
    Look for: related past changes, contributors who touched relevant files,
    why current patterns exist, previous attempts at similar features.
    Write findings to tmp/plans/{timestamp}/research/git-history.md.
    Claim task #3 via TaskList/TaskUpdate.
    See agents/research/git-miner.md for full instructions.`,
  run_in_background: true
})
```

### Phase 1B: Research Decision

After local research completes, evaluate whether external research is needed.

**Risk classification** (multi-signal scoring):

| Signal | Weight | Examples |
|---|---|---|
| Keywords in feature description | 40% | `security`, `auth`, `payment`, `API`, `crypto` |
| File paths affected | 30% | `src/auth/`, `src/payments/`, `.env`, `secrets` |
| External API integration | 20% | API calls, webhooks, third-party SDKs |
| Framework-level changes | 10% | Upgrades, breaking changes, new dependencies |

- HIGH_RISK >= 0.65: Always run external research
- LOW_RISK < 0.35: May skip external if local sufficiency is high
- UNCERTAIN 0.35-0.65: Always run external research

**Local sufficiency scoring** (when to skip external):

| Signal | Weight | Min Threshold |
|---|---|---|
| Matching echoes found | 35% | >= 1 Etched or >= 2 Inscribed |
| Codebase patterns discovered | 25% | >= 2 distinct patterns with evidence |
| Git history continuity | 20% | Recent commit (within 3 months) |
| Documentation completeness | 15% | Clear section + examples in CLAUDE.md |
| User familiarity flag | 5% | `--skip-research` flag |

- SUFFICIENT >= 0.70: Skip external research
- WEAK < 0.50: Must run external research
- MODERATE 0.50-0.70: Run external to confirm

### Phase 1C: External Research (conditional)

Spawn only if the research decision requires external input:

```javascript
// Only spawned if risk >= 0.65 OR local sufficiency < 0.70
TaskCreate({ subject: "Research best practices", description: "..." })      // #4
TaskCreate({ subject: "Research framework docs", description: "..." })      // #5

Task({
  team_name: "rune-plan-{timestamp}",
  name: "practice-seeker",
  subagent_type: "general-purpose",
  prompt: `You are Practice Seeker. Research best practices for: {feature}.
    Write findings to tmp/plans/{timestamp}/research/best-practices.md.
    Claim task #4 via TaskList/TaskUpdate.
    See agents/research/practice-seeker.md for full instructions.`,
  run_in_background: true
})

Task({
  team_name: "rune-plan-{timestamp}",
  name: "codex-scholar",
  subagent_type: "general-purpose",
  prompt: `You are Codex Scholar. Research framework docs for: {feature}.
    Write findings to tmp/plans/{timestamp}/research/framework-docs.md.
    Claim task #5 via TaskList/TaskUpdate.
    See agents/research/codex-scholar.md for full instructions.`,
  run_in_background: true
})
```

If external research times out: proceed with local findings only and recommend `--forge` re-run after implementation.

### Phase 1D: Spec Validation (always runs)

After 1A and 1C complete, run flow analysis:

```javascript
TaskCreate({ subject: "Spec flow analysis", description: "..." })          // #6

Task({
  team_name: "rune-plan-{timestamp}",
  name: "flow-seer",
  subagent_type: "general-purpose",
  prompt: `You are Flow Seer. Analyze the feature spec for completeness: {feature}.
    Identify: user flow gaps, edge cases, missing requirements, interaction issues.
    Write findings to tmp/plans/{timestamp}/research/specflow-analysis.md.
    Claim task #6 via TaskList/TaskUpdate.
    See agents/utility/flow-seer.md for full instructions.`,
  run_in_background: true
})
```

### Monitor Research

Poll TaskList every 30 seconds until all active research tasks are completed.

```javascript
while (not all research tasks completed):
  tasks = TaskList()
  if (all active tasks completed): break
  if (any stale > 5 min): proceed with partial
  sleep(30)
```

## Phase 2: Synthesize

After research completes, the lead consolidates findings.

### Plan Detail Level Selection

Before drafting, ask the user for detail level:

```javascript
AskUserQuestion({
  questions: [{
    question: "What detail level for this plan?",
    header: "Detail",
    options: [
      { label: "Standard (Recommended)", description: "Overview, solution, technical approach, criteria, references" },
      { label: "Minimal", description: "Brief description + acceptance criteria only" },
      { label: "Comprehensive", description: "Full spec with phases, alternatives, risks, ERD, metrics" }
    ],
    multiSelect: false
  }]
})
```

### Consolidation

1. Read all research output files from `tmp/plans/{timestamp}/research/`
2. Identify common themes, conflicting advice, key patterns
3. Draft the plan document (template varies by detail level):

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

## Phase 3: Forge (Optional — `--forge` flag)

If `--forge` is specified, spawn research agents to enrich each plan section with structured subsections.

### Default --forge Mode

For each major plan section, spawn a research agent that produces structured subsections:

```javascript
// Create forge tasks blocked by synthesis
TaskCreate({ subject: "Forge: {section 1}" })
TaskCreate({ subject: "Forge: {section 2}" })
// ... one per major section

// Each forge task gets a research agent
Task({
  team_name: "rune-plan-{timestamp}",
  name: "forge-researcher-{n}",
  subagent_type: "general-purpose",
  prompt: `Enrich plan section "{section}" with structured subsections.
    Write enhancements to tmp/plans/{timestamp}/forge/{section}.md`,
  run_in_background: true
})
```

Each forge agent produces these structured subsections:

```markdown
### Best Practices
{From practice-seeker — industry standards, community conventions}

### Performance Considerations
{From ember-oracle perspective via Forge Warden Runebearer}

### Security Considerations
{From Ward Sentinel Runebearer — OWASP, auth, input validation}

### Edge Cases
{From flaw-hunter perspective via Forge Warden Runebearer}

### Pattern Alignment
{From pattern-seer perspective via Pattern Weaver Runebearer}

### References
{Consolidated links from all agents}
```

In default `--forge` mode, perspectives from review agents (ember-oracle, flaw-hunter, pattern-seer) are provided through their parent Runebearers, not as standalone agents.

After forge completes, merge enrichments into the plan document.

### --exhaustive Mode (`--forge --exhaustive`)

When `--exhaustive` is combined with `--forge`, spawn ALL available agents per section:

```
Default --forge:    6 research agents per section
With --exhaustive:  ALL available agents per section (max 8 per section, configurable)

Agent selection for --exhaustive:
  1. Read rune-config.yml for custom Runebearers
  2. Collect: 6 research + 5 Runebearers (embedding 10 review perspectives) + N custom
  3. For each plan section:
     - Spawn ALL agents with the section as context
     - Each agent contributes from its expertise area
     - Two-tier aggregation: agents → per-section synthesizer → lead
  4. Max 5 concurrent agents per phase (enforced by orchestrator)
```

In `--exhaustive` mode, review agents may be spawned individually rather than through Runebearers.

**Spawn throttle enforcement**:
1. Max 5 concurrent agents per phase
2. Concurrent arc run prevention: check for active `.claude/arc/*/checkpoint.json`
3. Per-section sufficiency gate: apply local sufficiency scoring, skip agents whose expertise is covered

**Cost warning** (displayed before spawning):

```
--exhaustive mode will spawn {N} agents x {M} sections = {N*M} agent invocations.
Estimated token usage: ~{estimate}M tokens (~${cost_estimate}).
Token budget: {budget}M. Proceed? [Y/n]
```

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
4. /forge — Enhance each section with parallel research agents
5. Technical review — Run decree-arbiter + scroll-reviewer + knowledge-keeper
6. Create issue — Push to GitHub Issues
```

## Error Handling

| Error | Recovery |
|-------|----------|
| Research agent timeout (>5 min) | Proceed with partial research |
| No git history (git-miner) | Skip, report gap |
| No echoes (echo-reader) | Skip, proceed without history |
| Scroll review finds critical gaps | Address before presenting |
