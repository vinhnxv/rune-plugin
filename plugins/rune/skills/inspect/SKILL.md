---
name: inspect
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
disable-model-invocation: false
argument-hint: "[plan-file.md | inline description] [--mode plan|implementation] [--focus <dimension>] [--dry-run] [--fix]"
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

**Load skills**: `roundtable-circle`, `context-weaving`, `rune-echoes`, `rune-orchestration`, `polling-guard`, `zsh-compat`, `goldmask`

## Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--focus <dimension>` | Focus on a specific dimension: correctness, completeness, security, failure-modes, performance, design, observability, tests, maintainability | All dimensions |
| `--max-agents <N>` | Limit total Inspector Ashes (1-4) | 4 |
| `--dry-run` | Show scope, requirements, and inspector assignments without summoning agents | Off |
| `--threshold <N>` | Override completion threshold for READY verdict (0-100) | 80 |
| `--fix` | After VERDICT, spawn gap-fixer to auto-fix FIXABLE findings | Off |
| `--max-fixes <N>` | Cap on fixable gaps per run | 20 |
| `--mode <mode>` | Inspection mode: `implementation` (default) or `plan` | implementation |
| `--no-lore` | Disable Phase 1.3 Lore Layer (git history risk scoring) | Off |

**Dry-run mode** executes Phase 0 + Phase 0.5 + Phase 1 only. Displays: extracted requirements with IDs and priorities, inspector assignments, relevant codebase files, estimated team size. No teams, tasks, state files, or agents are created.

## 4 Inspector Ashes

| Inspector | Dimensions | Priority |
|-----------|-----------|----------|
| `grace-warden` | Correctness, Completeness | 1st |
| `ruin-prophet` | Security, Failure Modes | 2nd |
| `sight-oracle` | Performance, Design | 3rd |
| `vigil-keeper` | Observability, Tests, Maintainability | 4th |

For full prompt templates, focus mode, --max-agents redistribution, and --fix gap-fixer protocol — see [inspector-prompts.md](references/inspector-prompts.md).

## Phase 0: Pre-flight

### Step 0.1 — Parse Input

```
input = $ARGUMENTS

if (input matches /\.(md|txt)$/):
  // SEC-003: Validate plan path BEFORE filesystem access
  // SEC-001 FIX: Regex guard must run before fileExists() to prevent information oracle
  if (!/^[a-zA-Z0-9._\/-]+$/.test(input) || input.includes('..')):
    error("Invalid plan path: contains unsafe characters or path traversal")
  if (!fileExists(input)):
    error("Plan file not found: " + input)
  planPath = input
  planContent = Read(planPath)
  mode = "file"
else:
  planContent = input
  planPath = null
  mode = "inline"

if (!planContent || planContent.trim().length < 10):
  error("Plan is empty or too short.")

// Parse inspect mode flag
const inspectMode = flag("--mode") ?? "implementation"
// SEC: validate against fixed allowlist
if (!["implementation", "plan"].includes(inspectMode)):
  error("Unknown --mode value. Valid: implementation, plan")
```

### Step 0.2 — Read Talisman Config

```javascript
const config = readTalisman()
const inspectConfig = config?.inspect ?? {}

// RUIN-001 FIX: Runtime clamping prevents misconfiguration-based DoS/bypass
maxInspectors = Math.max(1, Math.min(4, flag("--max-agents") ?? inspectConfig.max_inspectors ?? 4))
timeout = Math.max(60_000, Math.min(inspectConfig.timeout ?? 720_000, 3_600_000))
completionThreshold = Math.max(0, Math.min(100, flag("--threshold") ?? inspectConfig.completion_threshold ?? 80))
gapThreshold = Math.max(0, Math.min(100, inspectConfig.gap_threshold ?? 20))
```

### Step 0.3 — Generate Identifier

```javascript
identifier = Date.now().toString(36)  // e.g., "lz5k8m2"
if (!/^[a-zA-Z0-9_-]+$/.test(identifier)):
  error("Invalid identifier generated")
outputDir = `tmp/inspect/${identifier}`
```

## Phase 0.5: Classification

### Step 0.5.1 — Extract Requirements

Follow the algorithm in [plan-parser.md](../roundtable-circle/references/plan-parser.md):

1. Parse YAML frontmatter (if present)
2. Extract requirements from explicit sections (Requirements, Deliverables, Tasks)
3. Extract requirements from implementation sections (Files to Create/Modify)
4. Fallback: extract action sentences from full text
5. Extract plan identifiers (file paths, code names, config keys)

```javascript
parsedPlan = parsePlan(planContent)
requirements = parsedPlan.requirements
identifiers = parsedPlan.identifiers

if (requirements.length === 0):
  error("No requirements could be extracted from the plan.")

// Plan mode: additionally extract code blocks as reviewable artifacts
if (inspectMode === "plan"):
  // Extract up to 20 code blocks, each capped at 1500 chars
```

### Steps 0.5.2–0.5.4 — Assign, Focus, Limit

1. **Assign** requirements to inspectors via keyword-based classification (plan-parser.md Step 5)
2. **Apply `--focus`**: redirect all requirements to a single inspector
3. **Apply `--max-agents`**: redistribute cut-inspector requirements to grace-warden

See [inspector-prompts.md](references/inspector-prompts.md) for step-by-step logic.

## Phase 1: Scope

### Step 1.1 — Identify Relevant Codebase Files

```javascript
scopeFiles = []

for (const id of identifiers):
  if (id.type === "file"):
    matches = Glob(id.value)
    scopeFiles.push(...matches)
  elif (id.type === "code"):
    matches = Grep(id.value, { output_mode: "files_with_matches", head_limit: 10 })
    scopeFiles.push(...matches)
  elif (id.type === "config"):
    matches = Grep(id.value, { glob: "*.{yml,yaml,json,toml,env}", output_mode: "files_with_matches", head_limit: 5 })
    scopeFiles.push(...matches)

// Deduplicate
scopeFiles = [...new Set(scopeFiles)]

// Plan mode: plan file is primary scope; only keep existing files
if (inspectMode === "plan" && planPath):
  scopeFiles = scopeFiles.filter(f => f === planPath || exists(f))

// Cap at 120 files (30 per inspector max)
if (scopeFiles.length > 120):
  scopeFiles = scopeFiles.slice(0, 120)
```

### Step 1.2 — Dry-Run Output

If `--dry-run`, display scope + assignments and stop. No teams, tasks, or agents created.

## Phase 1.3: Lore Layer (Risk Intelligence)

Runs AFTER scope is known (Phase 1) but BEFORE team creation (Phase 2). Discovers existing risk-map or spawns `lore-analyst` as a bare Task (no team yet — ATE-1 exemption). Re-sorts `scopeFiles` by risk tier and enriches requirement classification.

See [data-discovery.md](../goldmask/references/data-discovery.md) for the discovery protocol and [risk-context-template.md](../goldmask/references/risk-context-template.md) for prompt injection format.

### Skip Conditions

| Condition | Effect |
|-----------|--------|
| `talisman.goldmask.enabled === false` | Skip Phase 1.3 entirely |
| `talisman.goldmask.inspect.enabled === false` | Skip Phase 1.3 entirely |
| `talisman.goldmask.layers.lore.enabled === false` | Skip Phase 1.3 entirely |
| `--no-lore` flag | Skip Phase 1.3 entirely |
| Non-git repo | Skip Phase 1.3 |
| < 5 commits in lookback window (G5 guard) | Skip Phase 1.3 |
| `talisman.goldmask.inspect.wisdom_passthrough === false` | Skip wisdom injection in Phase 3 only |
| Existing risk-map found (>= 30% scope overlap) | Reuse instead of spawning agent |

### Step 1.3.1 — Skip Gate

```javascript
const goldmaskEnabled = config?.goldmask?.enabled !== false
const inspectGoldmaskEnabled = config?.goldmask?.inspect?.enabled !== false
const loreEnabled = config?.goldmask?.layers?.lore?.enabled !== false
const noLoreFlag = flag("--no-lore")
const isGitRepo = Bash("git rev-parse --is-inside-work-tree 2>/dev/null").trim() === "true"

let riskMap = null       // string | null — raw JSON from risk-map.json
let wisdomData = null    // string | null — raw markdown from wisdom-report.md

if (!goldmaskEnabled || !inspectGoldmaskEnabled || !loreEnabled || noLoreFlag || !isGitRepo) {
  warn("Phase 1.3: Lore Layer skipped — " + skipReason)
  // Proceed to Phase 2 without risk data
} else {
  // G5 guard: require minimum commit history
  const lookbackDays = config?.goldmask?.layers?.lore?.lookback_days ?? 180
  const commitCount = parseInt(
    Bash(`git rev-list --count HEAD --since='${lookbackDays} days ago' 2>/dev/null || echo 0`)
  )
  if (commitCount < 5) {
    warn("Phase 1.3: Lore Layer skipped — fewer than 5 commits in lookback window (G5 guard)")
  } else {
    // Step 1.3.2 — Discover or spawn
  }
}
```

### Step 1.3.2 — Discover Existing Risk-Map or Spawn Lore-Analyst

```javascript
// Option A: Reuse existing risk-map from prior workflows
const existing = discoverGoldmaskData({
  needsRiskMap: true,
  maxAgeDays: 3,
  scopeFiles: scopeFiles  // 30% overlap validation
})

if (existing?.riskMap) {
  riskMap = existing.riskMap
  warn(`Phase 1.3: Reusing existing risk-map from ${existing.riskMapPath}`)
} else {
  // Option B: Spawn lore-analyst as bare Task (ATE-1 exemption — no team exists yet)
  Task({
    subagent_type: "general-purpose",
    name: "inspect-lore-analyst",
    // NO team_name — ATE-1 exemption (pre-team phase, team created at Phase 2)
    prompt: `You are rune:investigation:lore-analyst.
Analyze git history risk for the following scope files.
Write risk-map.json to ${outputDir}/risk-map.json and lore-analysis.md to ${outputDir}/lore-analysis.md.

Scope files: ${scopeFiles.join(", ")}
Lookback days: ${lookbackDays}`
  })

  // Wait for completion (30s timeout, non-blocking)
  try {
    riskMap = Read(`${outputDir}/risk-map.json`)
  } catch (readError) {
    warn("Phase 1.3: lore-analyst output not available — proceeding without risk data")
    riskMap = null
  }
}

// Best-effort: load wisdom data if available (for Phase 3 injection)
const wisdomPassthrough = config?.goldmask?.inspect?.wisdom_passthrough !== false
if (wisdomPassthrough) {
  const wisdomResult = discoverGoldmaskData({
    needsRiskMap: false,
    needsWisdom: true,
    maxAgeDays: 7
  })
  if (wisdomResult?.wisdomReport) {
    wisdomData = wisdomResult.wisdomReport
  }
}
```

**Agent**: `lore-analyst` spawned as `general-purpose` with identity via prompt (ATE-1 compatible). Same pattern as appraise Phase 0.5.

**Output**: `tmp/inspect/{identifier}/risk-map.json` + `tmp/inspect/{identifier}/lore-analysis.md`

**Error handling**: If lore-analyst fails or times out, proceed without risk data. Non-blocking.

### Step 1.3.3 — Risk-Weighted Scope Sorting and Requirement Enhancement

```javascript
if (riskMap) {
  try {
    const parsed = JSON.parse(riskMap)
    const riskFiles = parsed?.files ?? []

    // Re-sort scopeFiles by risk tier: CRITICAL → HIGH → MEDIUM → LOW → STALE → unscored
    const tierOrder = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3, STALE: 4 }
    scopeFiles.sort((a, b) => {
      const aEntry = riskFiles.find(f => f.path === a)
      const bEntry = riskFiles.find(f => f.path === b)
      const aTier = tierOrder[aEntry?.tier] ?? 5
      const bTier = tierOrder[bEntry?.tier] ?? 5
      return aTier - bTier
    })

    // Enhance requirement classification with risk weighting
    for (const req of requirements) {
      const reqFiles = identifiers
        .filter(id => id.type === "file" && req.text.includes(id.value))
        .map(id => id.value)
      const maxRiskTier = getMaxRiskTier(reqFiles, riskFiles)

      if (maxRiskTier === 'CRITICAL') {
        req.inspectionPriority = 'HIGH'
        req.riskNote = "Touches CRITICAL-tier files — requires thorough inspection"
        // Dual inspector gate: only activate when plan has security-sensitive sections
        // OR talisman explicitly enables dual_inspector_gate
        const hasSecurity = requirements.some(r => /security|auth|crypt|token|inject|xss|sqli/i.test(r.text))
        const dualGateEnabled = inspectConfig.dual_inspector_gate ?? hasSecurity
        if (dualGateEnabled) {
          // Dual inspector assignment: grace-warden AND ruin-prophet
          req.assignedInspectors = ['grace-warden', 'ruin-prophet']
        }
      } else if (maxRiskTier === 'HIGH') {
        req.inspectionPriority = 'ELEVATED'
      }
    }
  } catch (parseError) {
    warn("Phase 1.3: risk-map.json parse error — proceeding without risk data")
    riskMap = null
  }
}

// Helper: returns highest risk tier from a list of files
function getMaxRiskTier(files: string[], riskFiles: RiskEntry[]): string {
  const tierOrder = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3, STALE: 4, UNKNOWN: 5 }
  let maxTier = 'UNKNOWN'
  for (const f of files) {
    const entry = riskFiles.find(r => r.path === f)
    const tier = entry?.tier ?? 'UNKNOWN'
    if ((tierOrder[tier] ?? 5) < (tierOrder[maxTier] ?? 5)) {
      maxTier = tier
    }
  }
  return maxTier
}
```

## Phase 2: Forge Team

```javascript
// Step 2.1 — Write state file with session isolation fields
const configDir = Bash(`cd "\${CLAUDE_CONFIG_DIR:-$HOME/.claude}" 2>/dev/null && pwd -P`).trim()
const ownerPid = Bash(`echo $PPID`).trim()
Write(`tmp/.rune-inspect-${identifier}.json`, JSON.stringify({
  status: "active", identifier, mode: inspectMode, plan_path: planPath,
  output_dir: outputDir, started: new Date().toISOString(),
  config_dir: configDir, owner_pid: ownerPid, session_id: "${CLAUDE_SESSION_ID}",
  inspectors: Object.keys(inspectorAssignments),
  requirement_count: requirements.length
}))

// Step 2.2 — Create output directory
Bash(`mkdir -p "tmp/inspect/${identifier}"`)

// Step 2.3 — Write inscription.json (output contract)
// Includes context budgets: grace-warden=40, ruin-prophet=30, sight-oracle=35, vigil-keeper=30
// instruction_anchoring: true, reanchor_interval: 5

// Step 2.4 — Pre-create guard (teamTransition pattern)
//   Step A: TeamDelete with retry-with-backoff (3 attempts: 0s, 3s, 8s)
//   Step B: Filesystem fallback if Step A failed (CDX-003 gate: !teamDeleteSucceeded)
//   Step C: Cross-workflow scan (stale inspect teams only — mmin +30)
const teamName = `rune-inspect-${identifier}`
// Validate: /^[a-zA-Z0-9_-]+$/ before any rm -rf

// Step 2.5 — Create team and signal dir
TeamCreate({ team_name: teamName })
// SEC-003: .readonly-active NOT created for inspect — inspectors need Write for output files
const signalDir = `tmp/.rune-signals/${teamName}`
Bash(`mkdir -p "${signalDir}"`)
Write(`${signalDir}/.expected`, String(Object.keys(inspectorAssignments).length))

// Step 2.6 — Create tasks (one per inspector + aggregator)
// Aggregator task blocked by all inspector tasks
```

## Phase 3: Summon Inspectors

Read and execute [inspector-prompts.md](references/inspector-prompts.md) for the full prompt generation contract, mode-aware template selection, inline plan sanitization, and --focus single-inspector logic.

**Key rules:**
- Summon all inspectors in a **single message** (parallel, `run_in_background: true`)
- All inspectors get full `scopeFiles` — they filter by relevance internally
- `model: "sonnet"` for each inspector
- Template path: `roundtable-circle/references/ash-prompts/{inspector}-inspect.md` (or `{inspector}-plan-review.md` for `--mode plan`)

### Step 3.1 — Risk Context Injection (Goldmask Enhancement)

If `riskMap` is available from Phase 1.3, inject risk context into each inspector's prompt using the [risk-context-template.md](../goldmask/references/risk-context-template.md) template.

```javascript
for (const inspector of inspectors) {
  const inspectorFiles = getFilesForInspector(inspector, requirements, scopeFiles)
  let riskContext = ""

  // Section 1+3: File Risk Tiers + Blast Radius from risk-map.json
  if (riskMap) {
    riskContext = renderRiskContextTemplate(riskMap, inspectorFiles)
  }

  // Section 2: Wisdom advisories passthrough
  if (wisdomData) {
    const advisories = filterWisdomForFiles(wisdomData, inspectorFiles)
    if (advisories.length > 0) {
      riskContext += "\n\n### Caution Zones\n\n"
      for (const adv of advisories) {
        riskContext += `- **\`${adv.file}\`** -- ${adv.intent} intent (caution: ${adv.cautionScore}). ${adv.advisory}\n`
      }
      riskContext += "\n**IMPORTANT**: Preserve the original design intent of these code sections."
      riskContext += " Your inspection must flag changes that break defensive, constraint, or compatibility behavior.\n"
    }
  }

  // Inspector-specific risk guidance notes
  if (riskContext) {
    if (inspector.name === 'grace-warden') {
      riskContext += "\n**Grace-warden note**: Prioritize completeness checks on CRITICAL-tier files."
      riskContext += " Requirements touching these files have outsized impact.\n"
    } else if (inspector.name === 'ruin-prophet') {
      riskContext += "\n**Ruin-prophet note**: CRITICAL-tier files with DEFENSIVE or CONSTRAINT intent"
      riskContext += " require extra scrutiny. These files guard against known failure modes.\n"
    } else if (inspector.name === 'sight-oracle') {
      riskContext += "\n**Sight-oracle note**: CRITICAL-tier files with high churn suggest unstable"
      riskContext += " architecture. Check for coupling issues.\n"
    } else if (inspector.name === 'vigil-keeper') {
      riskContext += "\n**Vigil-keeper note**: Files with ownership concentration (1-2 owners) have"
      riskContext += " bus factor risk. Check test coverage and documentation.\n"
    }

    inspector.prompt += "\n\n" + riskContext
  }
}
```

**Rendering rule**: Only inject when `riskContext` is non-empty. Empty risk context = omit entirely. See [risk-context-template.md](../goldmask/references/risk-context-template.md) for rendering rules.

## Phase 4: Monitor

```
POLL_INTERVAL = 30 seconds
maxIterations = ceil(timeout / 30_000)  // e.g., 24 for 12 min
staleCount: 3 consecutive no-progress polls → "Inspection appears stalled" warning

for (let i = 0; i < maxIterations; i++):
  1. Call TaskList                       ← MANDATORY every cycle
  2. Count completed vs totalTasks
  3. If completed === totalTasks → break
  4. Stale detection: 3 consecutive no-progress → break with warning
  5. Bash("sleep 30")
```

## Phase 5 + Phase 6: Verdict

Read and execute [verdict-synthesis.md](references/verdict-synthesis.md) for the full Verdict Binder aggregation, score aggregation, evidence verification, gap classification, and VERDICT.md structure.

**Summary:**
1. **Phase 5.2 (Verdict Binder)**: Aggregates inspector outputs. Produces VERDICT.md with requirement matrix, 9 dimension scores, gap analysis (8 categories), recommendations.
2. **Phase 5.3 (Wait)**: TaskList polling, 2-min timeout, 10s interval.
3. **Phase 6.1 (Evidence check)**: Verify up to 10 file references in VERDICT.md against disk.
4. **Phase 6.2 (Display)**: Show verdict summary (verdict, completion %, finding counts, report path).

### Phase 5-6 Enhancement: Historical Risk Assessment in VERDICT.md

If `riskMap` is available from Phase 1.3, the Verdict Binder includes a Historical Risk Assessment section in VERDICT.md. This section is appended AFTER the standard verdict sections.

```javascript
if (riskMap) {
  try {
    const parsed = JSON.parse(riskMap)
    const riskFiles = parsed?.files ?? []
    const tierOrder = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3, STALE: 4 }

    // Categorize files by tier
    const criticalFiles = riskFiles.filter(f => f.tier === 'CRITICAL')
    const highFiles = riskFiles.filter(f => f.tier === 'HIGH')
    const mediumFiles = riskFiles.filter(f => f.tier === 'MEDIUM')
    const lowFiles = riskFiles.filter(f => f.tier === 'LOW')

    // Single-owner files (bus factor risk)
    const singleOwnerFiles = riskFiles.filter(f =>
      f.metrics?.ownership?.distinct_authors === 1
    )

    // Build Historical Risk section
    let riskSection = "## Historical Risk Assessment (Goldmask Lore)\n\n"
    riskSection += "### File Risk Distribution\n\n"
    riskSection += "| Tier | Count | Files |\n"
    riskSection += "|------|-------|-------|\n"
    riskSection += `| CRITICAL | ${criticalFiles.length} | ${criticalFiles.map(f => '\`' + f.path + '\`').join(', ') || '--'} |\n`
    riskSection += `| HIGH | ${highFiles.length} | ${highFiles.map(f => '\`' + f.path + '\`').join(', ') || '--'} |\n`
    riskSection += `| MEDIUM | ${mediumFiles.length} | ... |\n`
    riskSection += `| LOW | ${lowFiles.length} | ... |\n\n`

    // Bus factor warnings
    if (singleOwnerFiles.length > 0) {
      riskSection += "### Bus Factor Warnings\n\n"
      for (const f of singleOwnerFiles.slice(0, 10)) {
        riskSection += `- \`${f.path}\`: single owner (${f.metrics?.ownership?.top_contributor ?? 'unknown'})\n`
      }
      riskSection += "\n"
    }

    // Inspection coverage vs risk
    riskSection += "### Inspection Coverage vs Risk\n\n"
    riskSection += "| Requirement | Risk Tier | Inspector Coverage | Finding Count |\n"
    riskSection += "|-------------|-----------|-------------------|---------------|\n"
    for (const req of requirements) {
      const reqTier = req.inspectionPriority === 'HIGH' ? 'CRITICAL'
        : req.inspectionPriority === 'ELEVATED' ? 'HIGH' : 'UNKNOWN'
      riskSection += `| ${req.id ?? req.text?.slice(0, 40)} | ${reqTier} | ${req.assignedInspectors?.length ?? 1} | -- |\n`
    }
    riskSection += "\n**Note**: Requirements touching CRITICAL files with zero findings"
    riskSection += " warrant manual review — they may represent gaps in inspection coverage.\n"

    // Append to VERDICT.md
    verdictContent += "\n\n" + riskSection
  } catch (parseError) {
    warn("Phase 5-6: risk-map parse error — omitting Historical Risk section from VERDICT")
  }
}
```

**Rendering rule**: The Historical Risk Assessment section is optional. If `riskMap` is null or parsing fails, the section is simply omitted from VERDICT.md. This is non-blocking.

## 9 Dimensions + 8 Gap Categories

### 9 Dimensions

| Dimension | Inspector | Description |
|-----------|-----------|-------------|
| Correctness | grace-warden | Logic implements requirements correctly |
| Completeness | grace-warden | All requirements implemented, no gaps |
| Security | ruin-prophet | Vulnerabilities, auth, input validation |
| Failure Modes | ruin-prophet | Error handling, retries, circuit breakers |
| Performance | sight-oracle | Bottlenecks, N+1 queries, memory leaks |
| Design | sight-oracle | Architecture, coupling, SOLID principles |
| Observability | vigil-keeper | Logging, metrics, tracing |
| Tests | vigil-keeper | Unit/integration coverage, test quality |
| Maintainability | vigil-keeper | Documentation, naming, complexity |

### 8 Gap Categories

| Category | Description |
|----------|-------------|
| MISSING | Requirement not implemented at all |
| INCOMPLETE | Partially implemented — edge cases missing |
| INCORRECT | Implemented but wrong — logic error |
| INSECURE | Security vulnerability or missing control |
| FRAGILE | Works but likely to break — missing error handling |
| UNOBSERVABLE | No logging/metrics/tracing |
| UNTESTED | No tests or insufficient coverage |
| UNMAINTAINABLE | Hard to change — excessive coupling, magic values |

## Phase 7: Cleanup

See [verdict-synthesis.md](references/verdict-synthesis.md) for full cleanup protocol.

**Summary:**
1. Shutdown all inspectors + verdict-binder (`SendMessage shutdown_request`)
2. `TeamDelete` with filesystem fallback (CHOME pattern)
3. Update state file to "completed" (preserve `config_dir`, `owner_pid`, `session_id`, verdict, completion)
4. Persist echo if P1 findings exist
5. If `--fix`: run Phase 7.5 remediation (gap-fixer team, 2-min timeout, append results to VERDICT.md)
6. Post-inspection: `AskUserQuestion` with options (View VERDICT, Fix gaps /rune:strive, /rune:appraise, Done)

## Error Handling

| Error | Recovery |
|-------|----------|
| Plan file not found | Error with file path suggestion |
| No requirements extracted | Error with plan format guidance |
| Inspector timeout | Proceed with available outputs |
| All inspectors failed | Error — no VERDICT possible |
| TeamCreate fails | Retry with pre-create guard |
| TeamDelete fails | Filesystem fallback (CHOME pattern) |
| VERDICT.md not created | Manual aggregation from inspector outputs |
| Lore-analyst timeout (Phase 1.3) | Proceed without risk data (WARN) |
| risk-map.json parse error (Phase 1.3) | Proceed without risk data (WARN) |
| Wisdom passthrough unavailable (Phase 3) | Skip wisdom injection (INFO) |
| Risk section render error (Phase 5-6) | Omit Historical Risk section from VERDICT (WARN) |

## Security

- Plan path validated with `/^[a-zA-Z0-9._\/-]+$/` before shell interpolation
- Team name validated with `/^[a-zA-Z0-9_-]+$/` before rm -rf
- Inspector outputs treated as untrusted (Truthbinding protocol)
- CHOME pattern used for all filesystem operations
- Inline plan sanitized before prompt injection (SEC-002, SEC-004)
- Inspector Ashes are read-only — they cannot modify the codebase
