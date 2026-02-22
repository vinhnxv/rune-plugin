---
name: plan
description: |
  Multi-agent planning workflow using Agent Teams. Combines brainstorm, research,
  validation, synthesis, shatter assessment, forge enrichment, and review into a
  single orchestrated pipeline with dependency-aware task scheduling.

  <example>
  user: "/rune:plan"
  assistant: "The Tarnished begins the planning ritual — full pipeline with brainstorm, forge, and review..."
  </example>

  <example>
  user: "/rune:plan --quick"
  assistant: "The Tarnished begins a quick planning ritual — research, synthesize, review only..."
  </example>
user-invocable: true
disable-model-invocation: false
argument-hint: "[--quick] [--no-brainstorm] [--no-forge] [--no-arena] [--exhaustive]"
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
  - Edit
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
  - WebSearch
  - WebFetch
  - mcp__plugin_compound-engineering_context7__resolve-library-id
  - mcp__plugin_compound-engineering_context7__query-docs
---

# /rune:plan — Multi-Agent Planning Workflow

**Load skills**: `roundtable-circle`, `context-weaving`, `rune-echoes`, `rune-orchestration`, `elicitation`, `codex-cli`, `polling-guard`, `zsh-compat`

Orchestrates a planning pipeline using Agent Teams with dependency-aware task scheduling.

## Usage

```
/rune:plan                              # Full pipeline (brainstorm + research + validate + synthesize + shatter? + forge + review)
/rune:plan --quick                      # Quick: research + synthesize + review only (skip brainstorm, forge, shatter)
```

### Legacy Flags (still functional, undocumented)

```
/rune:plan --no-brainstorm              # Skip brainstorm only (granular)
/rune:plan --no-forge                   # Skip forge only (granular)
/rune:plan --no-arena                   # Skip Arena only (granular)
/rune:plan --exhaustive                 # Exhaustive forge mode (lower threshold, research-budget agents)
/rune:plan --brainstorm                 # No-op (brainstorm is already default)
/rune:plan --forge                      # No-op (forge is already default)
```

## Pipeline Overview

```
Phase 0: Gather Input (brainstorm by default — auto-skip when requirements are clear)
    ↓
Phase 1: Research (up to 7 agents, conditional)
    ├─ Phase 1A: LOCAL RESEARCH (always — repo-surveyor, echo-reader, git-miner)
    ├─ Phase 1B: RESEARCH DECISION (risk + local sufficiency scoring)
    ├─ Phase 1C: EXTERNAL RESEARCH (conditional — practice-seeker, lore-scholar, codex-researcher)
    └─ Phase 1D: SPEC VALIDATION (always — flow-seer)
    ↓ (all research tasks converge)
Phase 1.5: Research Consolidation Validation (AskUserQuestion checkpoint)
    ↓
Phase 1.8: Solution Arena (competitive evaluation — skip with --quick or --no-arena)
    ↓
Phase 2: Synthesize (lead consolidates findings, detail level selection)
    ↓
Phase 2.3: Predictive Goldmask (risk scoring + wisdom advisories — skip with --quick)
    ↓
Phase 2.5: Shatter Assessment (complexity scoring → optional decomposition)
    ↓
Phase 3: Forge (default — skipped with --quick)
    ↓
Phase 4: Plan Review (scroll review + optional iterative refinement)
    ↓
Phase 4.5: Technical Review (optional — decree-arbiter + knowledge-keeper + codex-plan-reviewer)
    ↓
Phase 5: Echo Persist (save learnings to .claude/echoes/)
    ↓
Phase 6: Cleanup & Present (shutdown teammates, TeamDelete, present plan)
    ↓
Output: plans/YYYY-MM-DD-{type}-{name}-plan.md
        (or plans/YYYY-MM-DD-{type}-{name}-shard-N-plan.md if shattered)
```

## Phase 0: Gather Input

Runs a structured brainstorm session by default. Auto-detects recent brainstorms in `docs/brainstorms/` and `tmp/plans/*/brainstorm-decisions.md`. Skips when requirements are already clear.

**Skip conditions**: `--quick` flag, user provided specific acceptance criteria, scope is constrained and well-defined.

**Elicitation**: After approach selection, summons 1-3 elicitation-sage teammates (keyword-count fan-out, 15-keyword list). Skippable via `talisman.elicitation.enabled: false`.

**Output**: `tmp/plans/{timestamp}/brainstorm-decisions.md` with mandatory sections: Non-Goals, Constraint Classification, Success Criteria, Scope Boundary.

See [brainstorm-phase.md](references/brainstorm-phase.md) for the full protocol — all steps, elicitation sage spawning, decision capture templates, and ATE-1 compliance notes.

Read and execute when Phase 0 runs.

## Phase 1: Research (Conditional, up to 7 agents)

Spawns local research agents (repo-surveyor, echo-reader, git-miner), evaluates risk/sufficiency scores to decide on external research (practice-seeker, lore-scholar, codex-researcher), then runs spec validation (flow-seer). Includes research consolidation validation checkpoint.

**Inputs**: `feature` (sanitized string, from Phase 0), `timestamp` (validated identifier), talisman config
**Outputs**: Research agent outputs in `tmp/plans/{timestamp}/research/`, `inscription.json`
**Error handling**: TeamDelete fallback on cleanup, identifier validation before rm -rf, agent timeout (5 min) proceeds with partial findings

See [research-phase.md](references/research-phase.md) for the full protocol.

## Phase 1.8: Solution Arena

Generates competing solutions from research, evaluates on weighted dimensions, challenges with adversarial agents, and presents a decision matrix for approach selection.

**Skip conditions**: `--quick`, `--no-arena`, bug fixes, high-confidence refactors (confidence >= 0.9), sparse research (<2 viable approaches).

See [solution-arena.md](references/solution-arena.md) for full protocol (sub-steps 1.8A through 1.8D).

**Inputs**: Research outputs from `tmp/plans/{timestamp}/research/`, brainstorm-decisions.md (optional)
**Outputs**: `tmp/plans/{timestamp}/arena/arena-selection.md` (winning solution with rationale)
**Error handling**: Complexity gate skip → log reason. Sparse research → skip Arena. Agent timeout → proceed with partial. All solutions killed → recovery protocol.

## Phase 2: Synthesize

Tarnished consolidates research findings into a plan document. User selects detail level (Minimal/Standard/Comprehensive). Includes plan templates, formatting best practices, and the Plan Section Convention (contracts before pseudocode).

**Inputs**: Research outputs from `tmp/plans/{timestamp}/research/`, user detail level selection
**Outputs**: `plans/YYYY-MM-DD-{type}-{feature-name}-plan.md`
**Error handling**: Missing research files -> proceed with available data
**Comprehensive only**: Re-runs flow-seer on the drafted plan for a second SpecFlow pass

See [synthesize.md](references/synthesize.md) for the full protocol.

## Phase 2.3: Predictive Goldmask

After the plan is synthesized but before shatter assessment, runs a predictive Goldmask analysis to identify which existing files are likely to be affected, surface Wisdom advisories (caution zones) for risky areas, and inform the shatter decision with risk data.

**Skip conditions**: `--quick` mode, `talisman.goldmask.enabled === false`, non-git repo.

**Agents**: lore-analyst-prediction (risk scoring), wisdom-sage-prediction (design intent for CRITICAL/HIGH files).

**Note**: Phase 2.3 runs AFTER Phase 1, which creates the plan team (`rune-plan-{timestamp}`). All Task calls MUST use `team_name` (ATE-1 compliance — unlike Phase 0 sages which run before team creation).

**Talisman config** (`codex.shatter`):
- `enabled: true` — cross-model complexity scoring (default: true)
- `weight: 0.3` — Codex weight in blended score (default: 0.3, range: 0.0-1.0)

**Performance**: 50-170s total (1-3 min). Dominated by agent cold-start + git analysis.

**Non-blocking**: If Lore or Wisdom fails, the plan is written without the risk section. The pipeline continues to Phase 2.5.

## Phase 2.5: Shatter Assessment

Skipped when `--quick` is passed.

After synthesis produces a plan, assesses its complexity. If the plan is large enough to benefit from decomposition, offers to "shatter" it into smaller sub-plans (shards). Each shard is then forged and implemented independently.

### Complexity Scoring

| Signal | Weight | Threshold |
|--------|--------|-----------|
| Task count | 40% | >= 8 tasks |
| Phase count | 30% | >= 3 phases |
| Cross-cutting concerns | 20% | >= 2 shared dependencies |
| Estimated effort (sum of S/M/L) | 10% | >= 2 L-size phases |

Complexity score >= 0.65: Offer shatter. Score < 0.65: Skip, proceed to forge.

**Codex cross-model scoring** (optional): When Codex available, blends Claude + Codex scores (default weight: 0.3). Controlled via `talisman.codex.shatter.enabled`.

### Shatter Decision

When complexity >= 0.65, AskUserQuestion: Shatter (Recommended) / Keep as one plan / Let me choose sections.

### Shard Generation

1. Identify natural boundaries (implementation phases)
2. Create shard files: `plans/YYYY-MM-DD-{type}-{name}-shard-N-{phase-name}-plan.md`
3. Each shard: shared context section, specific phase tasks and acceptance criteria, dependencies on other shards
4. Parent plan updated with shard index and cross-shard dependency graph

After forge, `/rune:work` can target individual shards independently.

## Phase 3: Forge (Default — skipped with `--quick`)

Forge runs by default. Uses **Forge Gaze** (topic-aware agent matching) to select the best specialized agents for each plan section.

**Auto-trigger**: If user message contains ultrathink keywords (ULTRATHINK, DEEP, ARCHITECT), auto-enable `--exhaustive` forge mode.

### Default `--forge` Mode

- Parse plan into sections (## headings)
- Run Forge Gaze matching: threshold 0.30, max 3 agents/section, enrichment-budget agents only
- Summon throttle: max 5 concurrent, max 8 total agents
- Elicitation sages: up to MAX_FORGE_SAGES=6 per eligible section (keyword pre-filter)

### `--exhaustive` Mode

- Threshold: 0.15, max 5 agents/section, max 12 total
- Includes research-budget agents
- Two-tier aggregation
- Cost warning before summoning

**Fallback**: If no agent scores above threshold, use inline generic Task prompt for standard enrichment.

**Truthbinding**: All forge prompts include ANCHOR/RE-ANCHOR blocks. Plan content sanitized before injection (strip HTML comments, code fences, headings, HTML entities, zero-width chars).

See `roundtable-circle/references/forge-gaze.md` for the full topic registry and matching algorithm.

## Phase 4: Plan Review (Iterative)

Runs scroll-reviewer for document quality, then automated verification gate (deterministic checks including talisman patterns, universal checks, CommonMark compliance, measurability, filler detection). Optionally summons decree-arbiter, knowledge-keeper, and codex-plan-reviewer for technical review.

**Inputs**: Plan document from Phase 2/3, talisman config
**Outputs**: `tmp/plans/{timestamp}/scroll-review.md`, `tmp/plans/{timestamp}/decree-review.md`, `tmp/plans/{timestamp}/knowledge-review.md`, `tmp/plans/{timestamp}/codex-plan-review.md`
**Error handling**: BLOCK verdict -> address before presenting; CONCERN verdicts -> include as warnings
**Iterative**: Max 2 refinement passes for HIGH severity issues

See [plan-review.md](references/plan-review.md) for the full protocol.

## Phase 5: Echo Persist

Persist planning learnings to Rune Echoes:

```javascript
if (exists(".claude/echoes/planner/")) {
  appendEchoEntry(".claude/echoes/planner/MEMORY.md", {
    layer: "inscribed",
    source: `rune:plan ${timestamp}`,
    // ... key learnings from this planning session
  })
}
```

## Phase 6: Cleanup & Present

```javascript
// Resolve config directory once (CLAUDE_CONFIG_DIR aware)
const CHOME = Bash(`echo "\${CLAUDE_CONFIG_DIR:-$HOME/.claude}"`).trim()

// 1. Dynamic member discovery — reads team config to find ALL teammates
let allMembers = []
try {
  const teamConfig = Read(`${CHOME}/teams/rune-plan-${timestamp}/config.json`)
  const members = Array.isArray(teamConfig.members) ? teamConfig.members : []
  allMembers = members.map(m => m.name).filter(n => n && /^[a-zA-Z0-9_-]+$/.test(n))
} catch (e) {
  allMembers = [...allTeammates]
}

// Shutdown all discovered members
for (const member of allMembers) {
  SendMessage({ type: "shutdown_request", recipient: member, content: "Planning workflow complete" })
}

// 2. Wait for approvals (max 30s)

// 3. Cleanup team — QUAL-004: retry-with-backoff
// CRITICAL: Validate timestamp (/^[a-zA-Z0-9_-]+$/) before rm -rf — path traversal guard
if (!/^[a-zA-Z0-9_-]+$/.test(timestamp)) throw new Error("Invalid plan identifier")
if (timestamp.includes('..')) throw new Error('Path traversal detected')
const CLEANUP_DELAYS = [0, 3000, 8000]
for (let attempt = 0; attempt < CLEANUP_DELAYS.length; attempt++) {
  if (attempt > 0) Bash(`sleep ${CLEANUP_DELAYS[attempt] / 1000}`)
  try { TeamDelete(); break } catch (e) {
    if (attempt === CLEANUP_DELAYS.length - 1) warn(`plan cleanup: TeamDelete failed after ${CLEANUP_DELAYS.length} attempts`)
  }
}
Bash(`CHOME="\${CLAUDE_CONFIG_DIR:-$HOME/.claude}" && rm -rf "$CHOME/teams/rune-plan-${timestamp}/" "$CHOME/tasks/rune-plan-${timestamp}/" 2>/dev/null`)

// 4. Present plan to user
Read("plans/YYYY-MM-DD-{type}-{feature-name}-plan.md")
```

## Output

Plan file written to: `plans/YYYY-MM-DD-{type}-{feature-name}-plan.md`

**Filename examples**:
- `plans/2026-02-12-feat-user-authentication-plan.md`
- `plans/2026-02-12-fix-checkout-race-condition-plan.md`
- `plans/2026-02-12-refactor-api-client-plan.md`

After presenting the plan, offer next steps using AskUserQuestion:
- `/rune:work` → `Skill("rune:work", plan_path)`
- `/rune:forge` → `Skill("rune:forge", plan_path)`
- Open in editor → `Bash("open plans/${path}")` (macOS)
- Create issue → See [issue-creation.md](../rune-orchestration/references/issue-creation.md)

## Issue Creation

See [issue-creation.md](../rune-orchestration/references/issue-creation.md) for the full algorithm.

Read and execute when user selects "Create issue".

## Error Handling

| Error | Recovery |
|-------|----------|
| Research agent timeout (>5 min) | Proceed with partial research |
| No git history (git-miner) | Skip, report gap |
| No echoes (echo-reader) | Skip, proceed without history |
| Scroll review finds critical gaps | Address before presenting |

## Guardrails

Do not generate implementation code, test files, or configuration changes. This command produces research and plan documents only. If a research agent or forge agent starts writing implementation code, stop it and redirect to plan documentation. Code examples in plans are illustrative pseudocode only.
