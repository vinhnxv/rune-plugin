---
name: devise
description: |
  Multi-agent planning workflow using Agent Teams. Combines brainstorm, research,
  validation, synthesis, shatter assessment, forge enrichment, and review into a
  single orchestrated pipeline with dependency-aware task scheduling.

  <example>
  user: "/rune:devise"
  assistant: "The Tarnished begins the planning ritual — full pipeline with brainstorm, forge, and review..."
  </example>

  <example>
  user: "/rune:devise --quick"
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

# /rune:devise — Multi-Agent Planning Workflow

**Load skills**: `roundtable-circle`, `context-weaving`, `rune-echoes`, `rune-orchestration`, `elicitation`, `codex-cli`, `polling-guard`, `zsh-compat`

Orchestrates a planning pipeline using Agent Teams with dependency-aware task scheduling.

## Usage

```
/rune:devise                              # Full pipeline (brainstorm + research + validate + synthesize + shatter? + forge + review)
/rune:devise --quick                      # Quick: research + synthesize + review only (skip brainstorm, forge, shatter)
```

### Legacy Flags (still functional, undocumented)

```
/rune:devise --no-brainstorm              # Skip brainstorm only (granular)
/rune:devise --no-forge                   # Skip forge only (granular)
/rune:devise --no-arena                   # Skip Arena only (granular)
/rune:devise --exhaustive                 # Exhaustive forge mode (lower threshold, research-budget agents)
/rune:devise --brainstorm                 # No-op (brainstorm is already default)
/rune:devise --forge                      # No-op (forge is already default)
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

After the plan is synthesized but before shatter assessment, runs a predictive Goldmask analysis to identify which existing files are likely to be affected, surface Wisdom advisories (caution zones) for risky areas, trace dependency chains (Impact Layer), and inform the shatter decision with risk data.

**Skip conditions**: `--quick` mode, `talisman.goldmask.enabled === false`, `talisman.goldmask.devise.enabled === false`, non-git repo.

**Note**: Phase 2.3 runs AFTER Phase 1, which creates the plan team (`rune-plan-{timestamp}`). All Task calls MUST use `team_name` (ATE-1 compliance — unlike Phase 0 sages which run before team creation).

**Timeout inheritance**: Arc timeouts (from `talisman.arc.timeouts`) are NOT automatically propagated to Phase 2.3 devise agents. Phase 2.3 uses its own internal ceiling (`PHASE_23_TOTAL_CEILING_MS = 360_000`). If arc timeout is tighter than 6 min, Phase 2.3 agents may outlive the arc phase budget — ensure arc `forge` timeout accounts for Phase 2.3's contribution.

**Non-blocking**: If any agent fails, the pipeline continues with partial data. All failures are recoverable.

### Depth Modes

| Mode | Agents | Time | When to use |
|------|--------|------|-------------|
| `basic` (default) | 2 (lore + wisdom) | 50-170s | Standard planning — opt-in to enhanced for richer analysis |
| `enhanced` | 6 (lore + 3 tracers + wisdom + coordinator) | 2.5-5.5 min | Explicit opt-in: `goldmask.devise.depth: enhanced`. Budget ceiling: 6 min |
| `full` | 8 (lore + 5 tracers + wisdom + coordinator) | 3-6 min | Major architectural changes — explicit opt-in only |

**Talisman config**: `goldmask.devise.depth` — `basic` (default) | `enhanced` | `full`

### Step 0: Extract Predicted Files

Derive predicted affected files from Phase 1 research outputs (structured artifact),
NOT from regex parsing of free-form plan prose.

```javascript
const goldmaskEnabled: boolean = talisman?.goldmask?.enabled !== false
const goldmaskDeviseEnabled: boolean = talisman?.goldmask?.devise?.enabled !== false
const isGitRepo: boolean = Bash("git rev-parse --is-inside-work-tree 2>/dev/null").trim() === "true"
const isQuick: boolean = args.includes("--quick")

if (!goldmaskEnabled || !goldmaskDeviseEnabled || !isGitRepo || isQuick) {
  const skipReason: string = !goldmaskEnabled ? "goldmask.enabled=false"
    : !goldmaskDeviseEnabled ? "goldmask.devise.enabled=false"
    : !isGitRepo ? "not a git repo" : "--quick flag"
  warn(`Phase 2.3: Predictive Goldmask skipped — ${skipReason}`)
  // Continue to Phase 2.5
} else {
  const deviseDepth: string = talisman?.goldmask?.devise?.depth ?? "basic"
  // Validate depth value — fallback to basic for unrecognized values
  const validDepths: string[] = ["basic", "enhanced", "full"]
  const effectiveDepth: string = validDepths.includes(deviseDepth) ? deviseDepth : "basic"
  if (deviseDepth !== effectiveDepth) {
    warn(`Phase 2.3: Unrecognized depth "${deviseDepth}" — defaulting to "basic"`)
  }

  // Extract predicted files from Phase 1 research outputs (structured)
  // Prefer repo-surveyor output (contains file inventory), then git-miner (changed files)
  const predictedFiles: string[] = []
  try {
    const surveyorOutput: string = Read(`tmp/plans/${timestamp}/research/repo-analysis.md`)
    // Parse file paths from surveyor's file inventory section
    for (const match of surveyorOutput.matchAll(/`([^`]+\.\w+)`/g)) {
      const fp: string = match[1]
      if (fp && !fp.includes('..') && !predictedFiles.includes(fp)) {
        predictedFiles.push(fp)
      }
    }
  } catch (readError) {
    // Surveyor output unavailable — try git-miner
  }
  if (predictedFiles.length === 0) {
    try {
      const gitMinerOutput: string = Read(`tmp/plans/${timestamp}/research/git-history.md`)
      for (const match of gitMinerOutput.matchAll(/`([^`]+\.\w+)`/g)) {
        const fp: string = match[1]
        if (fp && !fp.includes('..') && !predictedFiles.includes(fp)) {
          predictedFiles.push(fp)
        }
      }
    } catch (readError) {
      // Git-miner output unavailable
    }
  }

  if (predictedFiles.length === 0) {
    warn("Phase 2.3: No predicted files found — falling back to basic mode")
    // Fall through to basic mode below
  }

  const outputDir: string = `tmp/plans/${timestamp}/goldmask-prediction`
  Bash(`mkdir -p "${outputDir}"`)
```

### Basic Mode (2 agents)

```javascript
  if (effectiveDepth === "basic" || predictedFiles.length === 0) {
    // Legacy behavior: lore-analyst + wisdom-sage only
    TaskCreate({ subject: "Lore analysis — risk scoring for predicted files" })
    TaskCreate({ subject: "Wisdom analysis — design intent for CRITICAL/HIGH files" })

    Task({
      team_name: `rune-plan-${timestamp}`,
      name: "devise-lore",
      subagent_type: "general-purpose",
      prompt: `You are rune:investigation:lore-analyst — a Goldmask Lore Layer analyst.

Analyze git history risk metrics for: ${predictedFiles.join(", ")}
Write risk-map.json to: ${outputDir}/risk-map.json

YOUR LIFECYCLE:
1. TaskList() -> claim "Lore analysis" task
2. Analyze git history, compute risk tiers
3. Write output, mark complete
4. Exit`,
      run_in_background: true
    })

    // Wait for lore, then spawn wisdom
    // ... standard polling (30s interval, 120s timeout)

    Task({
      team_name: `rune-plan-${timestamp}`,
      name: "devise-wisdom",
      subagent_type: "general-purpose",
      prompt: `You are rune:investigation:wisdom-sage — a Goldmask Wisdom Layer analyst.

Read risk-map: ${outputDir}/risk-map.json
Classify design intent for CRITICAL/HIGH risk files.
Write wisdom-report.md to: ${outputDir}/wisdom-report.md

YOUR LIFECYCLE:
1. TaskList() -> claim "Wisdom analysis" task
2. Read risk-map, analyze CRITICAL/HIGH files via git blame
3. Write wisdom report, mark complete
4. Exit`,
      run_in_background: true
    })

    // Wait for wisdom (120s timeout) — non-blocking on failure
```

### Enhanced Mode (6 agents — opt-in)

```javascript
  } else if (effectiveDepth === "enhanced") {
    // Phase 2.3a: 4 agents in parallel (lore + 3 Impact tracers)
    const PHASE_23A_TIMEOUT_MS: number = 90_000  // 90s for parallel phase
    const PHASE_23_TOTAL_CEILING_MS: number = 360_000  // 6 min hard ceiling
    // PER_AGENT_TIMEOUT_MS: lore=120s, each tracer=90s, wisdom=120s, coordinator=120s
    // Total sequential-worst-case: 90s (2.3a) + 120s (wisdom) + 120s (coordinator) = 330s < 360s ceiling
    // BACK-003: Enforce timeout budget before spawning 6 agents
    const phaseStartMs: number = Date.now()
    const perAgentTimeout: number = 120_000  // 2 min per agent (conservative upper bound)
    const estimatedTotalMs: number = PHASE_23A_TIMEOUT_MS + perAgentTimeout + perAgentTimeout  // 2.3a + wisdom + coordinator
    if (estimatedTotalMs > PHASE_23_TOTAL_CEILING_MS) {
      warn(`Phase 2.3: Enhanced mode estimated time (${Math.round(estimatedTotalMs / 1000)}s) exceeds hard ceiling (${Math.round(PHASE_23_TOTAL_CEILING_MS / 1000)}s) — falling back to basic mode`)
      // Explicit fallback: run basic mode agents (lore + wisdom) instead of doing nothing
      TaskCreate({ subject: "Lore analysis — risk scoring for predicted files" })
      TaskCreate({ subject: "Wisdom analysis — design intent for CRITICAL/HIGH files" })
      // ... spawn basic-mode lore-analyst and wisdom-sage (same as basic mode above)
    } else {

    TaskCreate({ subject: "Lore analysis — risk scoring for predicted files" })
    TaskCreate({ subject: "Business logic tracing — domain rule dependencies" })
    TaskCreate({ subject: "Data layer tracing — schema/ORM/migration cascade" })
    TaskCreate({ subject: "API contract tracing — endpoint/validator/doc impact" })

    // Spawn 4 agents in parallel
    Task({
      team_name: `rune-plan-${timestamp}`,
      name: "devise-lore",
      subagent_type: "general-purpose",
      prompt: `You are rune:investigation:lore-analyst — a Goldmask Lore Layer analyst.

Analyze git history risk metrics for: ${predictedFiles.join(", ")}
Lookback: ${talisman?.goldmask?.layers?.lore?.lookback_days ?? 180} days
Write risk-map.json to: ${outputDir}/risk-map.json

YOUR LIFECYCLE:
1. TaskList() -> claim "Lore analysis" task
2. Analyze git history, compute risk tiers (CRITICAL/HIGH/MEDIUM/LOW/STALE)
3. Write output, mark complete, exit`,
      run_in_background: true
    })

    Task({
      team_name: `rune-plan-${timestamp}`,
      name: "devise-business",
      subagent_type: "general-purpose",
      prompt: `You are rune:investigation:business-logic-tracer — a Goldmask Impact Layer tracer.

Trace business logic dependencies for: ${predictedFiles.join(", ")}
Identify domain rules, validation logic, and business constraints that depend on these files.
Write to: ${outputDir}/business-logic.md

YOUR LIFECYCLE:
1. TaskList() -> claim "Business logic tracing" task
2. Trace dependencies via Grep/Read, document domain rule chains
3. Write output, mark complete, exit`,
      run_in_background: true
    })

    Task({
      team_name: `rune-plan-${timestamp}`,
      name: "devise-data",
      subagent_type: "general-purpose",
      prompt: `You are rune:investigation:data-layer-tracer — a Goldmask Impact Layer tracer.

Trace data layer dependencies for: ${predictedFiles.join(", ")}
Identify schema definitions, ORM models, serializers, migrations that cascade from changes.
Write to: ${outputDir}/data-layer.md

YOUR LIFECYCLE:
1. TaskList() -> claim "Data layer tracing" task
2. Trace data flow via Grep/Read, document cascade paths
3. Write output, mark complete, exit`,
      run_in_background: true
    })

    Task({
      team_name: `rune-plan-${timestamp}`,
      name: "devise-api",
      subagent_type: "general-purpose",
      prompt: `You are rune:investigation:api-contract-tracer — a Goldmask Impact Layer tracer.

Trace API contract dependencies for: ${predictedFiles.join(", ")}
Identify endpoints, request/response schemas, validators, and documentation that would need updates.
Write to: ${outputDir}/api-contract.md

YOUR LIFECYCLE:
1. TaskList() -> claim "API contract tracing" task
2. Trace API surface via Grep/Read, document contract dependencies
3. Write output, mark complete, exit`,
      run_in_background: true
    })

    // Wait for Phase 2.3a agents (partial-ready gate: 3/4 complete within 90s starts wisdom early)
    // Standard polling: 30s interval, 90s timeout
    const phase23aStart: number = Date.now()
    let completedCount: number = 0
    while (Date.now() - phase23aStart < PHASE_23A_TIMEOUT_MS) {
      Bash("sleep 30")
      const tasks = TaskList()
      completedCount = countCompleted(tasks, ["Lore analysis", "Business logic", "Data layer", "API contract"])
      if (completedCount >= 4) break
      if (completedCount >= 3) {
        warn(`Phase 2.3a: ${completedCount}/4 complete — starting Wisdom Sage early (partial-ready gate)`)
        break
      }
    }
    if (completedCount < 3) {
      warn(`Phase 2.3a: Only ${completedCount}/4 agents completed within 90s — proceeding with partial data`)
    }

    // Phase 2.3b: Wisdom Sage (sequential — needs Impact outputs for context)
    TaskCreate({ subject: "Wisdom analysis — intent classification for CRITICAL/HIGH files" })
    Task({
      team_name: `rune-plan-${timestamp}`,
      name: "devise-wisdom",
      subagent_type: "general-purpose",
      prompt: `You are rune:investigation:wisdom-sage — a Goldmask Wisdom Layer analyst.

Classify developer intent for CRITICAL/HIGH risk files.
Read these inputs (skip any that are missing — partial data is acceptable):
- Risk map: ${outputDir}/risk-map.json
- Business logic report: ${outputDir}/business-logic.md
- Data layer report: ${outputDir}/data-layer.md
- API contract report: ${outputDir}/api-contract.md

Write wisdom-report.md to: ${outputDir}/wisdom-report.md

YOUR LIFECYCLE:
1. TaskList() -> claim "Wisdom analysis" task
2. Read available inputs, classify intent for CRITICAL/HIGH files
3. Write wisdom report with caution scores, mark complete, exit`,
      run_in_background: true
    })

    // Wait for Wisdom Sage (120s timeout)
    // ... standard polling (30s interval)

    // Phase 2.3c: Coordinator synthesis (sequential — needs all layer outputs)
    TaskCreate({ subject: "Coordinator synthesis — merge all layers into plan risk section" })
    Task({
      team_name: `rune-plan-${timestamp}`,
      name: "devise-coordinator",
      subagent_type: "general-purpose",
      prompt: `You are rune:investigation:goldmask-coordinator — Goldmask synthesis coordinator.

Synthesize predictive Goldmask analysis for planning. Read all available outputs from ${outputDir}/.

Produce GOLDMASK-PREDICTION.md with these sections:
1. "## Risk & Dependency Analysis (Goldmask Prediction)" — summary table
2. "### Predicted File Impact" — table with File, Risk Tier, Impact Type, Must Change?, Dependencies
3. "### Caution Zones" — wisdom advisories for CRITICAL/HIGH files
4. "### Collateral Damage Predictions" — what could break, cascade effects
5. "### MUST-CHANGE Files" — files the plan must address
6. "### SHOULD-CHECK Files" — files that may need changes

Write to: ${outputDir}/GOLDMASK-PREDICTION.md

YOUR LIFECYCLE:
1. TaskList() -> claim "Coordinator synthesis" task
2. Read all available layer outputs (skip missing — partial synthesis is OK)
3. Write GOLDMASK-PREDICTION.md, mark complete, exit`,
      run_in_background: true
    })

    // Wait for coordinator (120s timeout) — non-blocking on failure
    } // end enhanced-mode budget check
```

### Full Mode (8 agents)

```javascript
  } else if (effectiveDepth === "full") {
    // Full Goldmask: inline all 8 agents into existing plan team
    // NOTE: Cannot use Skill("rune:goldmask") here because it calls TeamCreate
    // internally, violating one-team-per-lead constraint. Instead, inline the
    // same agents directly into the rune-plan-{timestamp} team.
    warn("Phase 2.3: Full mode — inlining 8 Goldmask agents into plan team (3-5 min)")

    // Same as enhanced, but adds event-message-tracer and config-dependency-tracer
    // ... (lore + 5 tracers + wisdom + coordinator)
    // Implementation follows same pattern as enhanced with 2 additional tracers:
    //   devise-event (event-message-tracer) and devise-config (config-dependency-tracer)
    // Phase 2.3a spawns 6 agents (lore + 5 tracers) in parallel
    // Phase 2.3b and 2.3c remain identical to enhanced mode
  }
```

### Plan Injection

After coordinator completes, inject the prediction into the plan document:

```javascript
  // Read coordinator output
  try {
    const prediction: string = Read(`${outputDir}/GOLDMASK-PREDICTION.md`)
    // BACK-005: Validate all required sections are present before injecting
    const REQUIRED_SECTIONS: string[] = [
      "## Risk & Dependency Analysis (Goldmask Prediction)",
      "### Predicted File Impact",
      "### Caution Zones",
      "### Collateral Damage Predictions",
      "### MUST-CHANGE Files",
      "### SHOULD-CHECK Files"
    ]
    const missingSections: string[] = REQUIRED_SECTIONS.filter(s => !prediction.includes(s))
    if (missingSections.length > 0) {
      warn(`Phase 2.3: Coordinator output missing sections: ${missingSections.join(", ")} — skipping plan injection`)
    } else if (prediction && prediction.trim().length > 0) {
      // Insert after "## Non-Goals" section in the plan (before implementation phases)
      Edit(planPath, {
        old_string: "## Non-Goals",  // Find the Non-Goals heading
        new_string: `## Non-Goals`   // Keep it, insert prediction AFTER it via separate Edit
      })
      // Append prediction as new section after Non-Goals
      // Use section-end detection to find the right insertion point
      const planContent: string = Read(planPath)
      const nonGoalsEnd: number = findSectionEnd(planContent, "## Non-Goals")
      if (nonGoalsEnd > 0) {
        const insertionPoint: string = planContent.substring(nonGoalsEnd - 50, nonGoalsEnd)
        Edit(planPath, {
          old_string: insertionPoint,
          new_string: insertionPoint + "\n\n" + prediction
        })
        log("Phase 2.3: GOLDMASK-PREDICTION.md injected into plan")
      }
    }
  } catch (readError) {
    warn("Phase 2.3: Coordinator output missing — proceeding without prediction injection")
  }
} // end goldmask enabled check
```

### Phase Sequencing (Enhanced Mode)

```
Phase 2.3a (parallel, ~25-50s):
    +-- lore-analyst -> risk-map.json
    +-- business-logic-tracer -> business-logic.md
    +-- data-layer-tracer -> data-layer.md
    +-- api-contract-tracer -> api-contract.md

Phase 2.3b (sequential, ~60-120s):
    +-- wisdom-sage -> wisdom-report.md
        (reads impact reports + risk-map for context)

Phase 2.3c (sequential, ~60-90s):
    +-- goldmask-coordinator -> GOLDMASK-PREDICTION.md
        (synthesizes all layers into plan section)

Total: 2.5-4.5 min | Hard ceiling: 5 min
```

### Error Handling — Phase 2.3

| Phase | Error | Recovery | Severity |
|-------|-------|----------|----------|
| 2.3 | `extractPredictedFiles` returns 0 files | Fallback to basic mode | WARN |
| 2.3a | 1 of 3 Impact tracers fails | Proceed with partial — 2 of 3 reports | WARN |
| 2.3a | All 3 Impact tracers fail | Proceed Lore-only, coordinator gets minimal input | ERROR |
| 2.3a | All 4 parallel agents fail | Abort enhanced mode, skip to Phase 2.5 | ERROR |
| 2.3b | Wisdom Sage fails | Coordinator gets impact+lore without intent context | WARN |
| 2.3b | Wisdom Sage timeout (120s) | Same as failure — proceed without wisdom | WARN |
| 2.3c | Coordinator timeout (120s) | Skip plan injection, all upstream work wasted | ERROR |
| 2.3c | Malformed GOLDMASK-PREDICTION.md | Skip plan injection, warn user | ERROR |
| 2.3 | Unrecognized `depth` value | Treat as "basic", log warning | WARN |
| 2.3 | Team spawn failure | Fallback to basic mode | ERROR |

## Phase 2.3.5: Research Conflict Tiebreaker (Codex, v1.51.0)

**CONDITIONAL** — only runs when research agents produce conflicting recommendations. Most runs skip (~80% skip rate).

After Phase 2.3 Goldmask injection and before Phase 2.5 Shatter Assessment, detect conflicting recommendations from research agent outputs and invoke Codex for a tiebreaker verdict.

**Team**: None (inline codex exec within existing plan team — no new team)
**Output**: Tiebreaker verdict annotated inline in plan with `[CDX-TIEBREAKER]` tag
**Failure**: Non-blocking — conflicting recommendations preserved without tiebreaker annotation.

```javascript
// Phase 2.3.5: RESEARCH CONFLICT TIEBREAKER
// 4-condition detection gate (canonical pattern)
const codexAvailable = detectCodex()
const codexDisabled = talisman?.codex?.disabled === true
const tiebreakerEnabled = talisman?.codex?.research_tiebreaker?.enabled !== false  // Default ON
const workflowIncluded = (talisman?.codex?.workflows ?? []).includes("plan")

if (codexAvailable && !codexDisabled && tiebreakerEnabled && workflowIncluded) {
  // Step 1: Detect conflicts in research outputs
  // Read research agent outputs from Phase 1 (stored in plan team output directory)
  const researchOutputDir = `tmp/plans/${timestamp}/research/`
  const researchFiles = Glob(`${researchOutputDir}*.md`)

  // Conflict detection: look for contradictory recommendations
  // Parse each research output for recommendation sections and compare
  const recommendations = []
  for (const f of researchFiles) {
    try {
      const content = Read(f)
      // Extract recommendations from ## Recommendations or ## Approach sections
      const recMatch = content.match(/##\s*(?:Recommendations?|Approach|Conclusion|Verdict)\s*\n([\s\S]*?)(?=\n##|\n---|\Z)/i)
      if (recMatch) {
        recommendations.push({
          source: f.split('/').pop().replace('.md', ''),
          content: recMatch[1].trim().substring(0, 2000)
        })
      }
    } catch (e) { continue }
  }

  // Conflict detection gate: need at least 2 recommendations to compare
  if (recommendations.length < 2) {
    warn("Phase 2.3.5: Fewer than 2 research recommendations — skipping tiebreaker")
    // No output needed — tiebreaker is conditional
  } else {
    // Simple heuristic: check if recommendations mention different approaches
    // Look for contradictory signals (e.g., "REST" vs "GraphQL", "monolith" vs "microservices")
    const allText = recommendations.map(r => r.content).join("\n")
    const contradictionPairs = [
      [/\bREST\b/i, /\bGraphQL\b/i],
      [/\bmonolith/i, /\bmicroservice/i],
      [/\bSQL\b/i, /\bNoSQL\b/i],
      [/\bsynchronous\b/i, /\basynchronous\b/i],
      [/\bnot recommend/i, /\brecommend(?!.*not)\b/i]
    ]
    const hasConflict = contradictionPairs.some(([a, b]) => a.test(allText) && b.test(allText))

    if (!hasConflict) {
      warn("Phase 2.3.5: No conflicting recommendations detected — skipping tiebreaker")
    } else {
      // Conflict detected — invoke Codex for tiebreaker
      const { timeout, reasoning, model: codexModel } = resolveCodexConfig(talisman, "research_tiebreaker", {
        timeout: 300, reasoning: "high"
      })

      const promptTmpFile = `tmp/plans/${timestamp}/.codex-prompt-tiebreaker.tmp`
      try {
        const recSummary = recommendations.map(r =>
          `=== ${r.source} ===\n${sanitizePlanContent(r.content)}\n=== END ${r.source} ===`
        ).join("\n\n")

        const nonce = Bash(`openssl rand -hex 16`).trim()
        const promptContent = `SYSTEM: You are a cross-model research conflict resolver.

Research agents produced conflicting recommendations. Analyze each position and provide a tiebreaker verdict.

<<<NONCE_${nonce}>>>
${recSummary}
<<<END_NONCE_${nonce}>>>

Provide:
1. Summary of each position (1-2 sentences)
2. Key trade-offs between positions
3. Tiebreaker verdict: which approach to use and why
4. Confidence level (HIGH/MEDIUM/LOW)

Tag your verdict with [CDX-TIEBREAKER] for transparency.
Base analysis on technical merits, not assumptions.`

        Write(promptTmpFile, promptContent)
        const result = Bash(`"${CLAUDE_PLUGIN_ROOT}/scripts/codex-exec.sh" -m "${codexModel}" -r "${reasoning}" -t ${timeout} -j -g "${promptTmpFile}"`)
        const classified = classifyCodexError(result)

        if (classified === "SUCCESS" && result.stdout) {
          // Inject tiebreaker verdict into the plan document
          const verdict = result.stdout.substring(0, 3000)
          const planContent = Read(planPath)
          const tiebreakerSection = `\n\n### Research Conflict Resolution [CDX-TIEBREAKER]\n\n${verdict}\n`

          // Find the first ## heading after research section and inject before it
          // Or append after the last research-related section
          const injectionPoint = planContent.indexOf("## Implementation") !== -1
            ? planContent.indexOf("## Implementation")
            : planContent.indexOf("## Constraints") !== -1
              ? planContent.indexOf("## Constraints")
              : planContent.length
          Edit(planPath, {
            old_string: planContent.substring(injectionPoint, injectionPoint + 50),
            new_string: tiebreakerSection + planContent.substring(injectionPoint, injectionPoint + 50)
          })
          warn("Phase 2.3.5: Tiebreaker verdict injected into plan with [CDX-TIEBREAKER] tag")
        }
      } finally {
        Bash(`rm -f "${promptTmpFile}"`)  // Guaranteed cleanup
      }
    }
  }
} else {
  // Codex not available — skip silently (conditional phase, no output required)
  if (codexAvailable && !codexDisabled && tiebreakerEnabled) {
    warn("Phase 2.3.5: Skipped — plan not in codex.workflows")
  }
}
```

### Conflict Detection Heuristic

The heuristic uses simple keyword pair matching. It intentionally favors false positives (triggering tiebreaker when no real conflict exists) over false negatives (missing a real conflict). A false positive costs one Codex call (~$0.30); a false negative leaves conflicting advice unresolved.

### Error Handling — Phase 2.3.5

| Phase | Error | Recovery | Severity |
|-------|-------|----------|----------|
| 2.3.5 | No research outputs found | Skip silently | INFO |
| 2.3.5 | Fewer than 2 recommendations | Skip silently | INFO |
| 2.3.5 | No conflicts detected | Skip silently (expected ~80% of runs) | INFO |
| 2.3.5 | Codex timeout/error | Skip tiebreaker, proceed with conflicting recs | WARN |
| 2.3.5 | Plan injection fails | Log warning, proceed without annotation | WARN |

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

When complexity >= 0.65, AskUserQuestion with three options:

```javascript
AskUserQuestion({
  questions: [{
    question: "This plan is complex (score: ${complexityScore.toFixed(2)}). How would you like to proceed?",
    header: "Plan Decomposition",
    options: [
      {
        label: "Shatter (Recommended)",
        description: "Split into independent shard files executed separately. Best for parallel or loosely coupled work."
      },
      {
        label: "Hierarchical (parent + children)",
        description: "Decompose into parent plan with child sub-plans. Each child gets its own arc run with dependency DAG, requires/provides contracts, and branch strategy."
      },
      {
        label: "Keep as one plan",
        description: "Proceed without decomposition. Best for tightly coupled work that must stay together."
      },
      {
        label: "Let me choose sections",
        description: "Select which sections to split and which to keep together."
      }
    ],
    multiSelect: false
  }]
})
```

### Shard Generation

When "Shatter" is selected:

1. Identify natural boundaries (implementation phases)
2. Create shard files: `plans/YYYY-MM-DD-{type}-{name}-shard-N-{phase-name}-plan.md`
3. Each shard: shared context section, specific phase tasks and acceptance criteria, dependencies on other shards
4. Parent plan updated with shard index and cross-shard dependency graph

After forge, `/rune:strive` can target individual shards independently.

### Hierarchical Plan Generation

When "Hierarchical (parent + children)" is selected:

**Inputs**: planPath (string), planContent (string), planDir (string, dirname of planPath), timestamp (string)
**Outputs**: parentPlanPath (string), childPlanPaths (string[]), coherenceReport (string)
**Preconditions**: planPath validated, planDir writable
**Error handling**: mkdir failure → abort with message; child write failure → skip child, warn; circular dependency detected → halt and report

#### Phase 2.5A — Auto-generate requires/provides from task analysis

```javascript
// Analyze plan content for file references, imports, API routes, exported types
function extractContracts(planContent) {
  const contracts = { requires: [], provides: [] }

  // Detect file references (e.g., "src/models/User.ts")
  for (const match of planContent.matchAll(/`([^`]+\.\w{1,10})`/g)) {
    const fp = match[1]
    if (fp.includes('/') && !fp.includes('..')) {
      contracts.provides.push({ type: "file", name: fp })
    }
  }

  // Detect exported type/function references (e.g., "export interface UserDTO")
  for (const match of planContent.matchAll(/\bexport\s+(?:interface|type|class|function|const)\s+(\w+)/g)) {
    contracts.provides.push({ type: "export", name: match[1] })
  }

  // Detect API route references (e.g., "GET /api/users", "POST /auth/login")
  for (const match of planContent.matchAll(/\b(GET|POST|PUT|DELETE|PATCH)\s+(\/[\w/{}:]+)/g)) {
    contracts.provides.push({ type: "endpoint", name: `${match[1]} ${match[2]}` })
  }

  // Detect import dependencies (e.g., "depends on UserService")
  for (const match of planContent.matchAll(/\b(?:depends on|requires|imports?)\s+["`]?(\w[\w/.-]+)["`]?/gi)) {
    contracts.requires.push({ type: "file", name: match[1] })
  }

  return contracts
}
```

#### Phase 2.5B — Create children/ directory and generate child plans

```javascript
const childrenDir = `${planDir}/children`
Bash(`mkdir -p "${childrenDir}"`)

// Identify natural boundaries — each phase or major section becomes a child
const phases = extractImplementationPhases(planContent)
// phases: [{ name: "Foundation", tasks: [...], effort: "M" }, ...]

const childPlans = []
let prevChildPath = null

for (let i = 0; i < phases.length; i++) {
  const phase = phases[i]
  const childFileName = `${basename(planPath).replace('-plan.md', '')}-child-${i + 1}-${slugify(phase.name)}-plan.md`
  const childPath = `${childrenDir}/${childFileName}`

  // Determine depends_on from sequential ordering (each child depends on previous)
  // For parallel phases (same-level non-sequential tasks), depends_on = []
  const dependsOn = phase.canRunParallel ? [] : (prevChildPath ? [prevChildPath] : [])

  // Extract contracts from this phase's content
  const phaseContracts = extractContracts(phase.content)

  // Build requires from prior sibling provides
  const priorProvides = childPlans.flatMap(c => c.provides)
  const myRequires = phaseContracts.requires.filter(r =>
    priorProvides.some(p => p.type === r.type && p.name === r.name)
  )

  const childFrontmatter = `---
title: "${planFrontmatter.type}: ${phase.name} (child ${i + 1}/${phases.length})"
type: ${planFrontmatter.type}
date: ${today}
parent: "${planPath}"
sequence: ${i + 1}
depends_on: ${JSON.stringify(dependsOn)}
requires:
${myRequires.map(r => `  - type: ${r.type}\n    name: "${r.name}"`).join('\n')}
provides:
${phaseContracts.provides.map(p => `  - type: ${p.type}\n    name: "${p.name}"`).join('\n')}
status: pending
branch_suffix: "child-${i + 1}-${slugify(phase.name)}"
---`

  const childContent = `${childFrontmatter}

# ${phase.name} (Child ${i + 1} of ${phases.length})

> Part of hierarchical plan: [${basename(planPath)}](${planPath})

## Overview

${phase.description || `Implementation of ${phase.name} phase.`}

## Tasks

${phase.tasks.map(t => `- [ ] ${t}`).join('\n')}

## Acceptance Criteria

${phase.criteria.map(c => `- [ ] ${c}`).join('\n')}

## Requires (from prior children)

${myRequires.length > 0
    ? myRequires.map(r => `- **${r.type}**: \`${r.name}\``).join('\n')
    : '*(No prerequisites — this child can start immediately)*'}

## Provides (for subsequent children)

${phaseContracts.provides.map(p => `- **${p.type}**: \`${p.name}\``).join('\n')}

## References

- Parent plan: ${planPath}
`

  Write(childPath, childContent)
  childPlans.push({ path: childPath, name: phase.name, provides: phaseContracts.provides, requires: myRequires, dependsOn })
  prevChildPath = childPath
}
```

#### Phase 2.5C — Update parent plan with execution table and DAG

```javascript
// Build execution table for parent plan
const executionTable = `## Child Execution Table

| # | Child Plan | Status | Depends On | Branch |
|---|-----------|--------|------------|--------|
${childPlans.map((c, i) =>
  `| ${i + 1} | [${c.name}](${c.path}) | pending | ${c.dependsOn.length > 0 ? c.dependsOn.map(d => basename(d)).join(', ') : '—'} | feature/{id}/child-${i + 1} |`
).join('\n')}

## Dependency Contract Matrix

| Child | Requires | Provides |
|-------|---------|---------|
${childPlans.map(c =>
  `| ${c.name} | ${c.requires.map(r => `${r.type}:${r.name}`).join(', ') || '—'} | ${c.provides.map(p => `${p.type}:${p.name}`).join(', ') || '—'} |`
).join('\n')}
`

// Inject into parent plan before "## References"
const parentContent = Read(planPath)
Edit(planPath, {
  old_string: "## References",
  new_string: `${executionTable}\n## References`
})

// Also update parent frontmatter to mark it as hierarchical
const newFrontmatter = parentContent.replace(
  /^(---\n[\s\S]*?\n)---/,
  `$1children_dir: "${childrenDir}"\nhierarchical: true\n---`
)
Write(planPath, newFrontmatter)
```

#### Phase 2.5D — Cross-child coherence check

```javascript
// Validate: all children exist, no circular deps, task coverage
const coherenceFindings = []
const childPaths = new Set(childPlans.map(c => c.path))

// Check 1: All depends_on reference known children
for (const child of childPlans) {
  for (const dep of child.dependsOn) {
    if (!childPaths.has(dep)) {
      coherenceFindings.push(`MISSING_DEP: ${child.name} depends on unknown child: ${dep}`)
    }
  }
}

// Check 2: No circular dependencies (topological sort)
function hasCycle(nodes) {
  const visited = new Set()
  const inStack = new Set()
  function dfs(node) {
    visited.add(node)
    inStack.add(node)
    const deps = childPlans.find(c => c.path === node)?.dependsOn || []
    for (const dep of deps) {
      if (!visited.has(dep) && dfs(dep)) return true
      if (inStack.has(dep)) return true
    }
    inStack.delete(node)
    return false
  }
  return nodes.some(n => !visited.has(n) && dfs(n))
}
if (hasCycle(childPlans.map(c => c.path))) {
  coherenceFindings.push("CIRCULAR_DEP: Cycle detected in child dependency graph — halt generation")
}

// Check 3: Contract deduplication (same provides across children = conflict)
const allProvides = childPlans.flatMap(c => c.provides.map(p => ({ ...p, child: c.name })))
const seen = new Map()
for (const p of allProvides) {
  const key = `${p.type}:${p.name}`
  if (seen.has(key)) {
    coherenceFindings.push(`DUPLICATE_PROVIDES: Both ${seen.get(key)} and ${p.child} provide ${key}`)
  }
  seen.set(key, p.child)
}

// Check 4: All parent plan acceptance criteria covered by at least one child
const parentCriteria = extractAcceptanceCriteria(parentContent)
const childCriteria = childPlans.flatMap(c => extractAcceptanceCriteria(Read(c.path)))
for (const criterion of parentCriteria) {
  const covered = childCriteria.some(cc => cc.includes(criterion.slice(0, 40)))
  if (!covered) {
    coherenceFindings.push(`UNCOVERED_CRITERION: "${criterion.slice(0, 60)}..." not present in any child plan`)
  }
}

// Write coherence check output
const coherencePath = `tmp/plans/${timestamp}/coherence-check.md`
Bash(`mkdir -p "tmp/plans/${timestamp}"`)
Write(coherencePath, `# Coherence Check — ${today}\n\n${coherenceFindings.length === 0
  ? "All checks passed. No issues found."
  : coherenceFindings.map(f => `- [ ] ${f}`).join('\n')}\n`)

if (coherenceFindings.some(f => f.startsWith("CIRCULAR_DEP"))) {
  throw new Error("Hierarchical plan generation halted: circular dependency detected. See " + coherencePath)
}

if (coherenceFindings.length > 0) {
  warn(`Phase 2.5: ${coherenceFindings.length} coherence issue(s) found. Review ${coherencePath} before running arc-hierarchy.`)
}
```

After hierarchical generation completes, present summary to user:

```javascript
AskUserQuestion({
  questions: [{
    question: `Generated ${childPlans.length} child plans in ${childrenDir}/\n\nCoherence check: ${coherenceFindings.length === 0 ? "PASSED" : `${coherenceFindings.length} issues (see ${coherencePath})`}\n\nWhat would you like to do next?`,
    header: "Hierarchical Plan Ready",
    options: [
      { label: "Execute with /rune:arc-hierarchy", description: `Orchestrate all ${childPlans.length} children in dependency order` },
      { label: "Review child plans first", description: "Open parent plan and review the execution table" },
      { label: "Forge each child plan", description: "Run /rune:forge on each child to enrich with research" }
    ],
    multiSelect: false
  }]
})
```

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
    source: `rune:devise ${timestamp}`,
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
  const teamConfig = JSON.parse(Read(`${CHOME}/teams/rune-plan-${timestamp}/config.json`))
  const members = Array.isArray(teamConfig.members) ? teamConfig.members : []
  allMembers = members.map(m => m.name).filter(n => n && /^[a-zA-Z0-9_-]+$/.test(n))
} catch (e) {
  allMembers = []  // Team config unavailable — no members to shutdown
}

// Shutdown all discovered members
for (const member of allMembers) {
  SendMessage({ type: "shutdown_request", recipient: member, content: "Planning workflow complete" })
}

// 2. Grace period — let teammates deregister before TeamDelete
if (allMembers.length > 0) {
  Bash(`sleep 15`)
}

// 2.5. Mark state file as completed (deactivates ATE-1 enforcement for this workflow)
try {
  const stateFile = `tmp/.rune-plan-${timestamp}.json`
  const state = JSON.parse(Read(stateFile))
  Write(stateFile, { ...state, status: "completed" })
} catch (e) { /* non-blocking — state file may already be cleaned */ }

// 3. Cleanup team — QUAL-004: retry-with-backoff
// CRITICAL: Validate timestamp (/^[a-zA-Z0-9_-]+$/) before rm -rf — path traversal guard
if (!/^[a-zA-Z0-9_-]+$/.test(timestamp)) throw new Error("Invalid plan identifier")
if (timestamp.includes('..')) throw new Error('Path traversal detected')
const CLEANUP_DELAYS = [0, 5000, 10000]
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
- `/rune:strive` → `Skill("rune:strive", plan_path)`
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
| Solution Arena: all solutions killed | Recovery protocol — relax constraints, re-evaluate (see solution-arena.md) |
| Solution Arena: sparse research (<2 approaches) | Skip Arena, proceed to synthesize |
| Forge agent timeout (>5 min) | Proceed with partial enrichment |
| Forge: no agent above threshold | Use inline generic Task prompt for standard enrichment |
| Predictive Goldmask agent failure | Non-blocking — proceed with partial data or skip injection |
| Predictive Goldmask: enhanced budget exceeded | Fallback to basic mode (2 agents) |
| TeamCreate failure ("Already leading") | Catch-and-recover via teamTransition protocol |
| TeamDelete failure (cleanup) | Retry-with-backoff (3 attempts), filesystem fallback |
| Scroll review finds critical gaps | Address before presenting |
| Plan review BLOCK verdict | Address blocking issues before presenting plan |

## Guardrails

Do not generate implementation code, test files, or configuration changes. This command produces research and plan documents only. If a research agent or forge agent starts writing implementation code, stop it and redirect to plan documentation. Code examples in plans are illustrative pseudocode only.
