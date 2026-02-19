---
name: rune:inspect
description: |
  Plan-vs-implementation deep audit using Agent Teams. Parses a plan file (or inline description),
  extracts requirements, and summons 4 Inspector Ashes to measure implementation completeness,
  quality across 9 dimensions, and gaps across 8 categories. Produces a VERDICT.md with
  requirement matrix, dimension scores, gap analysis, and actionable recommendations.

  <example>
  user: "/rune:inspect plans/feat-user-auth-plan.md"
  assistant: "The Tarnished gazes upon the land, measuring what has been forged against what was decreed..."
  </example>

  <example>
  user: "/rune:inspect Add user authentication with JWT tokens and rate limiting"
  assistant: "The Tarnished inspects the codebase against the inline plan..."
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
---

# /rune:inspect — Plan-vs-Implementation Deep Audit

Orchestrate a multi-agent inspection that measures implementation completeness and quality against a plan. Each Inspector Ash gets its own 200k context window via Agent Teams.

**Load skills**: `roundtable-circle`, `context-weaving`, `rune-echoes`, `rune-orchestration`

## Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--focus <dimension>` | Focus on a specific dimension (correctness, security, performance, design, observability, tests, maintainability) | All dimensions |
| `--max-agents <N>` | Limit total Inspector Ashes (1-4) | 4 |
| `--dry-run` | Show scope, requirements, and inspector assignments without summoning agents | Off |
| `--threshold <N>` | Override completion threshold for READY verdict (0-100) | 80 (from talisman) |

**Dry-run mode** executes Phase 0 + Phase 0.5 + Phase 1 only, then displays:
- Extracted requirements with IDs and priorities
- Inspector assignments (which Ash handles which requirements)
- Relevant codebase files identified
- Estimated team size

No teams, tasks, state files, or agents are created.

## Phase 0: Pre-flight

### Step 0.1 — Parse Input

```
input = $ARGUMENTS

// Determine if input is a file path or inline text
if (input matches /\.(md|txt)$/ AND fileExists(input)):
  planPath = input
  planContent = Read(planPath)
  mode = "file"
else:
  // Inline mode: treat entire input as plan text
  planContent = input
  planPath = null
  mode = "inline"

// Validate plan content
if (!planContent || planContent.trim().length < 10):
  error("Plan is empty or too short. Provide a plan file path or describe requirements inline.")
```

### Step 0.2 — Read Talisman Config

```
// readTalisman() — same pattern as review.md, plan.md, work.md
config = readTalisman()
inspectConfig = config?.inspect ?? {}

maxInspectors = flag("--max-agents") ?? inspectConfig.max_inspectors ?? 4
timeout = inspectConfig.timeout ?? 720000  // 12 min
completionThreshold = flag("--threshold") ?? inspectConfig.completion_threshold ?? 80
gapThreshold = inspectConfig.gap_threshold ?? 20
```

### Step 0.3 — Generate Identifier

```
// Unique identifier for this inspection run
identifier = Date.now().toString(36)  // e.g., "lz5k8m2"

// Validate identifier
if (!/^[a-zA-Z0-9_-]+$/.test(identifier)):
  error("Invalid identifier generated")

outputDir = `tmp/inspect/${identifier}`
```

## Phase 0.5: Classification

### Step 0.5.1 — Extract Requirements

Follow the algorithm in [plan-parser.md](../skills/roundtable-circle/references/plan-parser.md):

1. Parse YAML frontmatter (if present)
2. Extract requirements from explicit sections (Requirements, Deliverables, Tasks)
3. Extract requirements from implementation sections (Files to Create/Modify)
4. Fallback: extract action sentences from full text
5. Extract plan identifiers (file paths, code names, config keys)

```
parsedPlan = parsePlan(planContent)
requirements = parsedPlan.requirements
identifiers = parsedPlan.identifiers

if (requirements.length === 0):
  error("No requirements could be extracted from the plan. Ensure the plan contains actionable items (lists, tasks, or sentences with action verbs).")
```

### Step 0.5.2 — Assign Requirements to Inspectors

Use keyword-based classification from plan-parser.md Step 5:

```
const inspectorAssignments = classifyRequirements(requirements)
// Result: { "grace-warden": ["REQ-001", ...], "ruin-prophet": [...], ... }
```

### Step 0.5.3 — Apply --focus Filter

```
if (flag("--focus")):
  focusDimension = flag("--focus")
  inspectorMap = {
    "correctness": "grace-warden",
    "security": "ruin-prophet",
    "performance": "sight-oracle",
    "design": "sight-oracle",
    "observability": "vigil-keeper",
    "tests": "vigil-keeper",
    "maintainability": "vigil-keeper"
  }
  if (!(focusDimension in inspectorMap)):
    error(`Unknown dimension: ${focusDimension}. Valid: ${Object.keys(inspectorMap).join(", ")}`)

  // Keep only the focused inspector
  focusedInspector = inspectorMap[focusDimension]
  // Reassign all requirements to the focused inspector
  inspectorAssignments = { [focusedInspector]: requirements.map(r => r.id) }
  maxInspectors = 1
```

### Step 0.5.4 — Apply --max-agents Limit

```
if (maxInspectors < 4):
  // Priority order: grace-warden > ruin-prophet > sight-oracle > vigil-keeper
  const priorityOrder = ["grace-warden", "ruin-prophet", "sight-oracle", "vigil-keeper"]
  const activeInspectors = priorityOrder.slice(0, maxInspectors)

  // Redistribute requirements from cut inspectors to remaining ones
  for (const [inspector, reqs] of Object.entries(inspectorAssignments)):
    if (!activeInspectors.includes(inspector)):
      // Assign to grace-warden (catch-all)
      inspectorAssignments["grace-warden"].push(...reqs)
      delete inspectorAssignments[inspector]
```

## Phase 1: Scope

### Step 1.1 — Identify Relevant Codebase Files

```
scopeFiles = []

// Search for files matching plan identifiers
for (const id of identifiers):
  if (id.type === "file"):
    // Direct file reference — check if it exists
    matches = Glob(id.value)
    scopeFiles.push(...matches)
  elif (id.type === "code"):
    // Code identifier — grep for it
    matches = Grep(id.value, { output_mode: "files_with_matches", head_limit: 10 })
    scopeFiles.push(...matches)
  elif (id.type === "config"):
    // Config key — search in config files
    matches = Grep(id.value, { glob: "*.{yml,yaml,json,toml,env}", output_mode: "files_with_matches", head_limit: 5 })
    scopeFiles.push(...matches)

// Deduplicate
scopeFiles = [...new Set(scopeFiles)]

// Cap at reasonable context budget
const MAX_SCOPE_FILES = 120  // 30 per inspector max
if (scopeFiles.length > MAX_SCOPE_FILES):
  scopeFiles = scopeFiles.slice(0, MAX_SCOPE_FILES)
```

### Step 1.2 — Dry-Run Output (if --dry-run)

```
if (flag("--dry-run")):
  // Display scope and assignments without creating anything
  log("=== /rune:inspect Dry Run ===")
  log("")
  log(`Plan: ${planPath || "(inline)"}`)
  log(`Mode: ${mode}`)
  log(`Requirements: ${requirements.length}`)
  log("")
  log("--- Requirements ---")
  for (const req of requirements):
    log(`  ${req.id} [${req.priority}] ${req.text.slice(0, 80)}`)
  log("")
  log("--- Inspector Assignments ---")
  for (const [inspector, reqs] of Object.entries(inspectorAssignments)):
    log(`  ${inspector}: ${reqs.length} requirements`)
  log("")
  log("--- Scope ---")
  log(`  Files identified: ${scopeFiles.length}`)
  for (const f of scopeFiles.slice(0, 20)):
    log(`    ${f}`)
  if (scopeFiles.length > 20):
    log(`    ... and ${scopeFiles.length - 20} more`)
  log("")
  log(`Estimated team size: ${Object.keys(inspectorAssignments).length} inspectors`)
  log("")
  log("[DRY RUN] No teams, tasks, or agents created.")
  return
```

## Phase 2: Forge Team

### Step 2.1 — Create State File

```
// Write state file for concurrency detection and rest.md cleanup
const stateFile = `tmp/.rune-inspect-${identifier}.json`
Write(stateFile, JSON.stringify({
  status: "active",
  identifier: identifier,
  plan_path: planPath,
  output_dir: outputDir,
  started: new Date().toISOString(),
  inspectors: Object.keys(inspectorAssignments),
  requirement_count: requirements.length
}))
```

### Step 2.2 — Create Output Directory

```bash
mkdir -p "tmp/inspect/${identifier}"
```

### Step 2.3 — Write Inscription

```
// inscription.json — output contract
const inscription = {
  workflow: "rune-inspect",
  timestamp: new Date().toISOString(),
  plan_path: planPath || "(inline)",
  output_dir: outputDir,
  teammates: [],
  aggregator: {
    name: "verdict-binder",
    output_file: "VERDICT.md"
  },
  context_engineering: {
    read_ordering: "source_first",
    instruction_anchoring: true,
    reanchor_interval: 5,
    context_budget: {
      "grace-warden": 40,
      "ruin-prophet": 30,
      "sight-oracle": 35,
      "vigil-keeper": 30
    }
  }
}

for (const [inspector, reqs] of Object.entries(inspectorAssignments)):
  inscription.teammates.push({
    name: inspector,
    output_file: `${inspector}.md`,
    required_sections: ["Dimension Scores", "P1 (Critical)", "P2 (High)", "P3 (Medium)", "Self-Review Log", "Summary"],
    role: inspectorRoleDescription(inspector),
    perspectives: inspectorPerspectives(inspector),
    file_scope: scopeFiles  // All inspectors see full scope — they filter by relevance
  })

Write(`${outputDir}/inscription.json`, JSON.stringify(inscription, null, 2))
```

### Step 2.4 — Pre-Create Guard

<!-- See team-lifecycle-guard.md for the canonical 3-step escalation pattern -->

```
const teamName = `rune-inspect-${identifier}`

// Validate team name
if (!/^[a-zA-Z0-9_-]+$/.test(teamName)):
  error("Invalid team name")

// Step A: Try TeamDelete in case of leftover
try { TeamDelete() } catch {}

// Step B: Filesystem cleanup
const CHOME = Bash(`echo "\${CLAUDE_CONFIG_DIR:-$HOME/.claude}"`).trim()
Bash(`rm -rf "${CHOME}/teams/${teamName}/" "${CHOME}/tasks/${teamName}/" 2>/dev/null`)

// Step C: Cross-workflow scan
Bash(`find "${CHOME}/teams/" -maxdepth 1 -type d -name "rune-inspect-*" -mmin +30 -exec rm -rf {} + 2>/dev/null`)
```

### Step 2.5 — Create Team

```
TeamCreate({
  team_name: teamName,
  description: `Inspect: ${planPath || "inline plan"} (${requirements.length} requirements)`
})
```

### Step 2.6 — Create Tasks

```
const tasks = []

for (const [inspector, reqIds] of Object.entries(inspectorAssignments)):
  const taskId = TaskCreate({
    subject: `${inspector}: Inspect ${reqIds.length} requirements`,
    description: `Inspector ${inspector} assesses requirements: ${reqIds.join(", ")}. Write findings to ${outputDir}/${inspector}.md`,
    activeForm: `${inspector} inspecting`
  })
  tasks.push({ inspector, taskId, reqIds })

// Aggregator task (blocked by all inspectors)
const aggregatorTaskId = TaskCreate({
  subject: "Verdict Binder: Aggregate inspection findings",
  description: `Aggregate all inspector outputs into ${outputDir}/VERDICT.md`,
  activeForm: "Aggregating verdict"
})

// Set aggregator dependency
for (const t of tasks):
  TaskUpdate({ taskId: aggregatorTaskId, addBlockedBy: [t.taskId] })
```

## Phase 3: Summon Inspectors

### Step 3.1 — Summon Inspector Ashes

For each inspector in `inspectorAssignments`, summon using the Task tool with Agent Teams:

```
// Build prompts from ash-prompt templates
// See: roundtable-circle/references/ash-prompts/{inspector}-inspect.md

for (const { inspector, taskId, reqIds } of tasks):
  const reqList = reqIds.map(id => {
    const req = requirements.find(r => r.id === id)
    return `- ${id} [${req.priority}]: ${req.text}`
  }).join("\n")

  const fileList = scopeFiles.join("\n")

  // Load prompt template and substitute variables
  const prompt = loadTemplate(`${inspector}-inspect.md`, {
    plan_path: planPath || "(inline plan embedded below)",
    output_path: `${outputDir}/${inspector}.md`,
    task_id: taskId,
    requirements: reqList,
    identifiers: identifiers.map(i => `${i.type}: ${i.value}`).join("\n"),
    scope_files: fileList,
    timestamp: new Date().toISOString()
  })

  // If inline mode, append plan content to prompt
  if (mode === "inline"):
    prompt += `\n\n## INLINE PLAN CONTENT\n\n${planContent}`

  Task({
    prompt: prompt,
    subagent_type: inspector,
    team_name: teamName,
    name: inspector,
    model: "sonnet",
    run_in_background: true
  })
```

### Step 3.2 — Agent Selection for --focus

When `--focus` is active, only 1 inspector is summoned. The remaining budget allows deeper analysis:

```
if (flag("--focus")):
  // Single inspector gets all requirements and larger context budget
  // Template already handles this via {requirements} substitution
```

## Phase 4: Monitor

### Step 4.1 — Polling Loop

<!-- DELEGATION-CONTRACT: Monitor loop follows polling-guard.md pattern -->

```
// waitForCompletion — correct TaskList-based polling
const pollIntervalMs = 30000  // 30 seconds
const maxIterations = Math.ceil(timeout / pollIntervalMs)  // 24 iterations for 12 min

for (let i = 0; i < maxIterations; i++):
  const taskList = TaskList()
  const completedTasks = taskList.filter(t => t.status === "completed")
  const totalTasks = taskList.length

  // Check if all tasks complete (including aggregator)
  if (completedTasks.length === totalTasks):
    log(`All ${totalTasks} tasks completed.`)
    break

  // Stale detection: if no progress for 3 consecutive polls
  if (i > 0 && completedTasks.length === previousCompleted):
    staleCount++
    if (staleCount >= 6):  // 3 minutes of no progress
      log("WARNING: Inspection appears stalled. Proceeding with available results.")
      break
  else:
    staleCount = 0
    previousCompleted = completedTasks.length

  // Progress log
  log(`[${i+1}/${maxIterations}] ${completedTasks.length}/${totalTasks} tasks completed`)

  // Sleep between polls
  Bash(`sleep ${pollIntervalMs / 1000}`)

// Timeout check
if (completedTasks.length < totalTasks):
  log(`WARNING: Inspection timed out. ${completedTasks.length}/${totalTasks} tasks completed.`)
```

## Phase 5: Aggregate

### Step 5.1 — Check Inspector Outputs

```
const inspectorOutputs = []
for (const inspector of Object.keys(inspectorAssignments)):
  const outputPath = `${outputDir}/${inspector}.md`
  if (fileExists(outputPath)):
    inspectorOutputs.push({ inspector, path: outputPath, status: "complete" })
  else:
    inspectorOutputs.push({ inspector, path: outputPath, status: "missing" })
    log(`WARNING: ${inspector} output missing at ${outputPath}`)
```

### Step 5.2 — Summon Verdict Binder

If all (or most) inspector outputs exist, summon the Verdict Binder to aggregate:

```
if (inspectorOutputs.filter(o => o.status === "complete").length === 0):
  error("No inspector outputs found. Inspection failed completely.")

// Build verdict-binder prompt from template
const verdictPrompt = loadTemplate("verdict-binder.md", {
  output_dir: outputDir,
  inspector_files: inspectorOutputs
    .filter(o => o.status === "complete")
    .map(o => `${o.inspector}.md`)
    .join(", "),
  plan_path: planPath || "(inline)",
  requirement_count: requirements.length,
  inspector_count: Object.keys(inspectorAssignments).length,
  timestamp: new Date().toISOString()
})

Task({
  prompt: verdictPrompt,
  subagent_type: "rune:utility:runebinder",
  team_name: teamName,
  name: "verdict-binder",
  model: "sonnet"
})
```

### Step 5.3 — Wait for Verdict

```
// Poll for VERDICT.md creation (short timeout — aggregation is fast)
const verdictTimeout = 120000  // 2 minutes
const verdictPollMs = 10000    // 10 seconds
const verdictMaxIter = Math.ceil(verdictTimeout / verdictPollMs)

for (let i = 0; i < verdictMaxIter; i++):
  if (fileExists(`${outputDir}/VERDICT.md`)):
    log("VERDICT.md created successfully.")
    break
  Bash(`sleep ${verdictPollMs / 1000}`)
```

## Phase 6: Verify

### Step 6.1 — Cross-Check Evidence

Read the VERDICT.md and perform lightweight verification:

```
const verdict = Read(`${outputDir}/VERDICT.md`)

// Verify: does VERDICT reference real files?
const fileRefs = verdict.match(/`([^`]+:\d+)`/g) || []
let verified = 0
let total = fileRefs.length

for (const ref of fileRefs.slice(0, 10)):  // Cap at 10 checks
  const [file, line] = ref.replace(/`/g, "").split(":")
  if (fileExists(file)):
    verified++

log(`Evidence verification: ${verified}/${Math.min(total, 10)} file references valid`)
```

### Step 6.2 — Display Verdict Summary

```
// Extract key metrics from VERDICT.md
// Show to user as immediate feedback
log("═══════════════════════════════════════════")
log("  INSPECTION VERDICT")
log("═══════════════════════════════════════════")
log(`  Plan: ${planPath || "(inline)"}`)
log(`  Requirements: ${requirements.length}`)
log(`  Verdict: ${extractVerdict(verdict)}`)
log(`  Completion: ${extractCompletion(verdict)}%`)
log(`  Findings: ${extractFindingCounts(verdict)}`)
log(`  Report: ${outputDir}/VERDICT.md`)
log("═══════════════════════════════════════════")
```

## Phase 7: Cleanup

### Step 7.1 — Shutdown Inspectors

```
// Send shutdown to all active teammates
for (const inspector of Object.keys(inspectorAssignments)):
  try:
    SendMessage({
      type: "shutdown_request",
      recipient: inspector,
      content: "Inspection complete. Shutting down."
    })
  catch: pass  // Inspector may have already exited

// Also shutdown verdict-binder if still active
try:
  SendMessage({
    type: "shutdown_request",
    recipient: "verdict-binder",
    content: "Aggregation complete. Shutting down."
  })
catch: pass
```

### Step 7.2 — TeamDelete with Fallback

```
// Wait briefly for shutdowns
Bash("sleep 5")

try:
  TeamDelete()
catch (e):
  // Filesystem fallback — team may have active members
  log(`TeamDelete failed: ${e.message}. Using filesystem fallback.`)
  const CHOME = Bash(`echo "\${CLAUDE_CONFIG_DIR:-$HOME/.claude}"`).trim()
  if (/^[a-zA-Z0-9_-]+$/.test(teamName)):
    Bash(`rm -rf "${CHOME}/teams/${teamName}/" "${CHOME}/tasks/${teamName}/" 2>/dev/null`)
```

### Step 7.3 — Update State File

```
const stateFile = `tmp/.rune-inspect-${identifier}.json`
const state = JSON.parse(Read(stateFile))
state.status = "completed"
state.completed = new Date().toISOString()
state.verdict = extractVerdict(verdict)
state.completion = extractCompletion(verdict)
Write(stateFile, JSON.stringify(state))
```

### Step 7.4 — Persist Echo (if significant findings)

```
// Persist to Rune Echoes if there are P1 findings
const p1Count = extractP1Count(verdict)
if (p1Count > 0):
  const echoContent = `## Inspection: ${planPath || "inline"}\n\n`
    + `Date: ${new Date().toISOString()}\n`
    + `Verdict: ${extractVerdict(verdict)}\n`
    + `P1 findings: ${p1Count}\n\n`
    + `Key gaps identified — see ${outputDir}/VERDICT.md`

  Write(`.claude/echoes/orchestrator/MEMORY.md`, echoContent, { append: true })
```

### Step 7.5 — Post-Inspection Actions

```
AskUserQuestion({
  questions: [{
    question: "Inspection complete. What would you like to do next?",
    header: "Next",
    options: [
      {
        label: "View VERDICT.md",
        description: `Open ${outputDir}/VERDICT.md for full findings`
      },
      {
        label: "Fix gaps (/rune:work)",
        description: "Generate a work plan from the P1/P2 gaps"
      },
      {
        label: "Review code (/rune:review)",
        description: "Run a standard code review on the implementation"
      },
      {
        label: "Done",
        description: "No further action needed"
      }
    ],
    multiSelect: false
  }]
})
```

## Helper Functions

### inspectorRoleDescription(name)

```
const roles = {
  "grace-warden": "Correctness and completeness assessment — requirement traceability",
  "ruin-prophet": "Failure modes, security posture, and operational readiness assessment",
  "sight-oracle": "Architecture alignment, coupling analysis, and performance profiling",
  "vigil-keeper": "Test coverage, observability, maintainability, and documentation assessment"
}
return roles[name]
```

### inspectorPerspectives(name)

```
const perspectives = {
  "grace-warden": ["feature-completeness", "logic-correctness", "domain-placement"],
  "ruin-prophet": ["failure-modes", "security-posture", "operational-readiness"],
  "sight-oracle": ["architecture-alignment", "coupling-analysis", "performance-profile"],
  "vigil-keeper": ["test-coverage", "observability", "maintainability", "documentation"]
}
return perspectives[name]
```

### extractVerdict(verdictContent)

```
const match = verdictContent.match(/Verdict\s*\|\s*\*\*(\w+)\*\*/)
return match ? match[1] : "UNKNOWN"
```

### extractCompletion(verdictContent)

```
const match = verdictContent.match(/Overall Completion\s*\|\s*(\d+)%/)
return match ? parseInt(match[1]) : 0
```

### extractP1Count(verdictContent)

```
const match = verdictContent.match(/P1:\s*(\d+)/)
return match ? parseInt(match[1]) : 0
```

### extractFindingCounts(verdictContent)

```
const p1 = extractP1Count(verdictContent)
const p2Match = verdictContent.match(/P2:\s*(\d+)/)
const p3Match = verdictContent.match(/P3:\s*(\d+)/)
return `${p1} P1, ${p2Match?.[1] ?? 0} P2, ${p3Match?.[1] ?? 0} P3`
```

## Error Handling

| Error | Recovery |
|-------|----------|
| Plan file not found | Error with file path suggestion |
| No requirements extracted | Error with plan format guidance |
| Inspector timeout | Proceed with available outputs |
| All inspectors failed | Error — no VERDICT possible |
| TeamCreate fails | Retry with pre-create guard |
| TeamDelete fails | Filesystem fallback |
| VERDICT.md not created | Manual aggregation from inspector outputs |

## Security

- Plan path validated with `/^[a-zA-Z0-9._\/-]+$/` before shell interpolation
- Team name validated with `/^[a-zA-Z0-9_-]+$/` before rm -rf
- Inspector outputs treated as untrusted (Truthbinding protocol)
- CHOME pattern used for all filesystem operations
- Identifier validated before path construction

## Notes

- Inspector Ashes are read-only — they cannot modify the codebase
- Each inspector gets its own 200k context window via Agent Teams
- The Verdict Binder aggregates findings without recalculating scores
- Inline mode embeds the plan text directly in inspector prompts
- `--focus` mode redirects all requirements to a single inspector for deeper analysis
- Completion threshold is configurable via talisman (`inspect.completion_threshold`)
