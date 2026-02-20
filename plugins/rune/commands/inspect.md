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
| `--focus <dimension>` | Focus on a specific dimension (correctness, completeness, security, failure-modes, performance, design, observability, tests, maintainability) | All dimensions |
| `--max-agents <N>` | Limit total Inspector Ashes (1-4) | 4 |
| `--dry-run` | Show scope, requirements, and inspector assignments without summoning agents | Off |
| `--threshold <N>` | Override completion threshold for READY verdict (0-100) | 80 (from talisman) |
| `--fix` | After VERDICT, spawn gap-fixer to auto-fix FIXABLE findings | Off |
| `--max-fixes <N>` | Cap on fixable gaps per run | 20 |

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
if (input matches /\.(md|txt)$/):
  // SEC-003: Validate plan path BEFORE filesystem access (same pattern as forge.md + arc.md)
  // SEC-001 FIX: Regex guard must run before fileExists() to prevent information oracle
  if (!/^[a-zA-Z0-9._\/-]+$/.test(input) || input.includes('..')):
    error("Invalid plan path: contains unsafe characters or path traversal")
  if (!fileExists(input)):
    error("Plan file not found: " + input)
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
    "completeness": "grace-warden",        // QUAL-002 FIX: was missing from 9-dimension system
    "security": "ruin-prophet",
    "failure-modes": "ruin-prophet",        // QUAL-002 FIX: was missing from 9-dimension system
    "performance": "sight-oracle",
    "design": "sight-oracle",
    "observability": "vigil-keeper",
    "tests": "vigil-keeper",
    "maintainability": "vigil-keeper"
  }
  if (!(focusDimension in inspectorMap)):
    // SEC-006 FIX: Use fixed error message — do not echo unvalidated user input
    error("Unknown --focus dimension. Valid: correctness, completeness, security, failure-modes, performance, design, observability, tests, maintainability")

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

// Step A: TeamDelete with retry-with-backoff (3 attempts: 0s, 3s, 8s)
let teamDeleteSucceeded = false
const RETRY_DELAYS = [0, 3000, 8000]
for (let attempt = 0; attempt < RETRY_DELAYS.length; attempt++):
  if (attempt > 0):
    warn(`teamTransition: TeamDelete attempt ${attempt + 1} failed, retrying in ${RETRY_DELAYS[attempt]/1000}s...`)
    Bash(`sleep ${RETRY_DELAYS[attempt] / 1000}`)
  try:
    TeamDelete()
    teamDeleteSucceeded = true
    break
  catch (e):
    if (attempt === RETRY_DELAYS.length - 1):
      warn(`teamTransition: TeamDelete failed after ${RETRY_DELAYS.length} attempts. Using filesystem fallback.`)

// Step B: Filesystem fallback (only when Step A failed — avoids blast radius on happy path)
// CDX-003 FIX: Gate behind !teamDeleteSucceeded to prevent cross-workflow scan from
// wiping concurrent workflows when TeamDelete already succeeded cleanly.
if (!teamDeleteSucceeded):
  Bash(`CHOME="\${CLAUDE_CONFIG_DIR:-$HOME/.claude}" && rm -rf "$CHOME/teams/${teamName}/" "$CHOME/tasks/${teamName}/" 2>/dev/null`)
  // Step C: Cross-workflow scan (stale inspect teams only)
  Bash(`CHOME="\${CLAUDE_CONFIG_DIR:-$HOME/.claude}" && find "$CHOME/teams/" -maxdepth 1 -type d -name "rune-inspect-*" -mmin +30 -exec rm -rf {} + 2>/dev/null`)
  try { TeamDelete() } catch (e2) { /* proceed to TeamCreate */ }
```

### Step 2.5 — Create Team

```
TeamCreate({
  team_name: teamName,
  description: `Inspect: ${planPath || "inline plan"} (${requirements.length} requirements)`
})

// SEC-003 FIX: .readonly-active REMOVED for inspect workflow.
// Inspector Ashes need Write to produce output files (tmp/inspect/{id}/{inspector}.md).
// enforce-readonly.sh blocks Write for ALL subagents when .readonly-active exists,
// which would prevent inspectors from writing findings — a functional conflict.
// Primary defense: Truthbinding protocol (prompt-level restriction).
// Secondary defense: Agent tools frontmatter limits tool surface.
// Signal dir still created for team lifecycle tracking (without .readonly-active marker).
const signalDir = `tmp/.rune-signals/${teamName}`
Bash(`mkdir -p "${signalDir}"`)
Write(`${signalDir}/.expected`, String(Object.keys(inspectorAssignments).length))
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

  // If inline mode, append plan content to prompt with sanitization delimiter
  // SEC-004: Wrap inline content with data boundary to prevent prompt structure interference
  if (mode === "inline"):
    const sanitizedPlan = planContent
      .replace(/<!--[\s\S]*?-->/g, '')           // Strip HTML comments (prompt injection vector)
      .replace(/^#{1,6}\s+/gm, '')               // Strip markdown headings (prompt override vector)
      .replace(/<\/plan-data>/gi, '')             // SEC-002 FIX: Strip closing delimiter to prevent boundary escape
      .replace(/<[^>]+>/g, '')                    // SEC-002 FIX: Strip all XML-style tags (defense-in-depth)
      .slice(0, 10000)                            // Cap at 10KB
    prompt += `\n\n## INLINE PLAN CONTENT\n\n<plan-data>\n${sanitizedPlan}\n</plan-data>`

  // ATE-1: All multi-agent commands MUST use subagent_type: "general-purpose" with identity via prompt
  Task({
    prompt: prompt,
    subagent_type: "general-purpose",
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

// ATE-1: Uses general-purpose with runebinder-style aggregation prompt (same as review.md Runebinder)
Task({
  prompt: verdictPrompt,
  subagent_type: "general-purpose",
  team_name: teamName,
  name: "verdict-binder",
  model: "sonnet",
  run_in_background: true
})
```

### Step 5.3 — Wait for Verdict

```
// BACK-004 FIX: Use TaskList-based polling instead of fileExists (Core Rule 9 compliance)
// SEC-007 FIX: Eliminates symlink-based TOCTOU race on VERDICT.md
const verdictResult = waitForCompletion(teamName, 1, {
  timeoutMs: 120_000,        // 2 minutes (aggregation is fast)
  staleWarnMs: 60_000,       // 1 minute
  pollIntervalMs: 10_000,    // 10 seconds
  label: "Verdict Binder"
})

if (verdictResult.timedOut):
  warn("Verdict Binder timed out — checking for partial output")
if (!fileExists(`${outputDir}/VERDICT.md`) || Bash(`test -L "${outputDir}/VERDICT.md" && echo symlink`).trim() === 'symlink'):
  error("VERDICT.md not produced. Check Verdict Binder output for errors.")
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

  // BACK-002: Write() does not support { append: true }. Read existing content first, concatenate, then Write.
  const existingEchoes = exists(`.claude/echoes/orchestrator/MEMORY.md`)
    ? Read(`.claude/echoes/orchestrator/MEMORY.md`) : ""
  Write(`.claude/echoes/orchestrator/MEMORY.md`, existingEchoes + "\n" + echoContent)
```

## Phase 7.5: Remediation

> Activated only when `--fix` flag is set. Spawns the gap-fixer Ash to auto-remediate FIXABLE findings from VERDICT.md.

### Step 7.5.1 — Gate Check

```
if (!flag("--fix")):
  // Proceed to Step 7.6 (Post-Inspection Actions)
  goto step_7_6
```

### Step 7.5.2 — Parse Fixable Gaps

```
const fixableGaps = parseFixableGaps(`${outputDir}/VERDICT.md`)
const maxFixes = flag("--max-fixes") ?? inspectConfig.max_fixes ?? 20
const cappedGaps = fixableGaps.slice(0, maxFixes)

log(`Remediation: ${fixableGaps.length} FIXABLE gaps found, capping at ${cappedGaps.length}`)

if (cappedGaps.length === 0):
  log("No FIXABLE gaps found — skipping remediation phase.")
  goto step_7_6
```

### Step 7.5.3 — Group by File and Create Tasks

```
// Group gaps by target file for batching
const gapsByFile = cappedGaps.reduce((acc, gap) => {
  const file = gap.file || "unknown"
  if (!acc[file]) acc[file] = []
  acc[file].push(gap)
  return acc
}, {})

const fixerTasks = []
for (const [file, gaps] of Object.entries(gapsByFile)):
  const taskId = TaskCreate({
    subject: `gap-fixer: fix ${gaps.length} gap(s) in ${file}`,
    description: `Fix FIXABLE gaps in ${file}: ${gaps.map(g => g.id).join(", ")}`,
    activeForm: `Fixing gaps in ${file}`
  })
  fixerTasks.push({ file, gaps, taskId })
```

### Step 7.5.4 — Spawn Gap-Fixer Agent

```
// Write gap-fix state file so validate-gap-fixer-paths.sh hook activates (SEC-GAP-001)
const gapFixStateFile = `tmp/.rune-gap-fix-${identifier}.json`
Write(gapFixStateFile, JSON.stringify({
  status: "active",
  identifier: identifier,
  source: "inspect-fix",
  started: new Date().toISOString(),
  gaps: cappedGaps.map(g => g.id)
}))

// Create a new team for remediation phase
const fixerTeamName = `rune-inspect-fixer-${identifier}`
TeamCreate({
  team_name: fixerTeamName,
  description: `Gap remediation for inspect run ${identifier}`
})

// Load gap-fixer prompt template
const fixerPrompt = loadTemplate("gap-fixer.md", {
  verdict_path: `${outputDir}/VERDICT.md`,
  output_dir: outputDir,
  identifier: identifier,
  gaps: cappedGaps.map(g =>
    `- [ ] **[${g.id}]** ${g.description} — \`${g.file}:${g.line}\``
  ).join("\n"),
  timestamp: new Date().toISOString()
})

Task({
  prompt: fixerPrompt,
  subagent_type: "general-purpose",
  team_name: fixerTeamName,
  name: "gap-fixer",
  model: "sonnet",
  run_in_background: true
})
```

### Step 7.5.5 — Monitor and Shutdown Fixer

```
// Wait for gap-fixer to complete (2 min timeout)
const fixerResult = waitForCompletion(fixerTeamName, fixerTasks.length, {
  timeoutMs: 120_000,
  staleWarnMs: 60_000,
  pollIntervalMs: 10_000,
  label: "Gap Fixer"
})

// Shutdown fixer
try:
  SendMessage({
    type: "shutdown_request",
    recipient: "gap-fixer",
    content: "Remediation complete. Shutting down."
  })
catch: pass

Bash("sleep 3")

try:
  TeamDelete()
catch (e):
  const CHOME = Bash(`echo "\${CLAUDE_CONFIG_DIR:-$HOME/.claude}"`).trim()
  if (/^[a-zA-Z0-9_-]+$/.test(fixerTeamName)):
    Bash(`rm -rf "${CHOME}/teams/${fixerTeamName}/" "${CHOME}/tasks/${fixerTeamName}/" 2>/dev/null`)

// Clean up gap-fix state file
const gapFixState = JSON.parse(Read(gapFixStateFile))
gapFixState.status = "completed"
gapFixState.completed = new Date().toISOString()
Write(gapFixStateFile, JSON.stringify(gapFixState))
```

### Step 7.5.6 — Append Remediation Results to VERDICT.md

```
// Read the remediation report written by gap-fixer
const remediationReportPath = `${outputDir}/remediation-report.md`
if (fileExists(remediationReportPath)):
  const remediationReport = Read(remediationReportPath)
  const existingVerdict = Read(`${outputDir}/VERDICT.md`)
  Write(`${outputDir}/VERDICT.md`, existingVerdict + "\n\n" + remediationReport)
  log("Remediation results appended to VERDICT.md")
else:
  log("WARNING: Remediation report not produced at " + remediationReportPath)
```

### Step 7.6 — Post-Inspection Actions

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

### parseFixableGaps(verdictContent)

Parses FIXABLE gap entries from VERDICT.md. Entries must match the pattern:
`- [ ] **[PREFIX-NUM]** description — \`file:line\``

```
function parseFixableGaps(verdictPath) {
  const content = Read(verdictPath)
  const gaps = []

  // Match checkbox gap entries with file:line references (SEC-GAP-003: bounded capture groups)
  const GAP_PATTERN = /^- \[ \] \*\*\[([A-Z0-9_-]{1,20})\]\*\* (.{1,200}) — `([^`:\n]{1,200}):(\d{1,6})`/gm

  let match
  while ((match = GAP_PATTERN.exec(content)) !== null):
    const [, id, description, file, line] = match

    // Classify fixability
    // MANUAL gaps: architectural, design-level, or explicitly marked MANUAL
    const isManual = /\b(MANUAL|architectural|redesign|breaking change|schema migration)\b/i.test(description)
    const classification = isManual ? "MANUAL" : "FIXABLE"

    if (classification === "FIXABLE"):
      gaps.push({
        id: id,           // e.g., "GRACE-001", "VEIL-003" — capped at 20 chars (SEC-GAP-003)
        description: description,  // capped at 200 chars (SEC-GAP-003)
        file: file,
        line: parseInt(line, 10),
        classification: "FIXABLE"
      })

  return gaps
}
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
