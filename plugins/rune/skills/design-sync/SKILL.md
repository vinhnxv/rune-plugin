---
name: design-sync
description: |
  Figma design synchronization workflow. Extracts design specs from Figma URLs,
  creates Visual Spec Maps (VSM), guides implementation workers, and reviews
  fidelity between design and code. 3-phase pipeline: PLAN (extraction) ->
  WORK (implementation) -> REVIEW (fidelity check).

  <example>
  user: "/rune:design-sync https://www.figma.com/design/abc123/MyApp?node-id=1-3"
  assistant: "Initiating design sync — extracting Figma specs and creating VSM..."
  </example>

  <example>
  user: "/rune:design-sync --review-only"
  assistant: "Running design fidelity review against existing VSM..."
  </example>
user-invocable: true
disable-model-invocation: false
argument-hint: "<figma-url> [--plan-only] [--resume-work] [--review-only]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - Agent
  - TaskCreate
  - TaskUpdate
  - TaskGet
  - TaskList
  - TeamCreate
  - TeamDelete
  - SendMessage
  - AskUserQuestion
---

**Runtime context** (preprocessor snapshot):
- Active workflows: !`grep -rl '"active"' tmp/.rune-*-*.json 2>/dev/null | wc -l | tr -d ' '`
- Current branch: !`git branch --show-current 2>/dev/null || echo "unknown"`

# /rune:design-sync — Figma Design Synchronization

Extracts design specifications from Figma, creates Visual Spec Maps (VSM), coordinates implementation, and reviews design-to-code fidelity.

**Load skills**: `frontend-design-patterns`, `figma-to-react`, `context-weaving`, `rune-orchestration`, `polling-guard`, `zsh-compat`

## Usage

```
/rune:design-sync <figma-url>                        # Full pipeline: extract → implement → review
/rune:design-sync <figma-url> --plan-only            # Extract VSM only (no implementation)
/rune:design-sync --resume-work                      # Resume from existing VSM
/rune:design-sync --review-only                      # Review fidelity of existing implementation
```

## Prerequisites

1. **Figma MCP server** configured in `.mcp.json` with `FIGMA_TOKEN` environment variable
2. **design_sync.enabled** set to `true` in talisman.yml (default: false)
3. Frontend framework detected in project (React, Vue, Next.js, Vite)

## Pipeline Overview

```
Phase 0: Pre-Flight → Validate URL, check MCP availability, read talisman config
    |
Phase 1: Design Extraction (PLAN) → Fetch Figma data, create VSM files
    |
Phase 1.5: User Confirmation → Show VSM summary, confirm or edit before implementation
    |
Phase 2: Implementation (WORK) → Create components from VSM using swarm workers
    |
Phase 2.5: Design Iteration → Optional screenshot→analyze→fix loop for fidelity
    |
Phase 3: Fidelity Review (REVIEW) → Score implementation against VSM
    |
Phase 4: Cleanup → Shutdown workers, persist echoes, report results
```

## Phase 0: Pre-Flight

```
// Step 1: Parse arguments
figmaUrl = $ARGUMENTS[0]
flags = parseFlags($ARGUMENTS)  // --plan-only, --resume-work, --review-only

// Step 2: Validate Figma URL
FIGMA_URL_PATTERN = /^https:\/\/www\.figma\.com\/(design|file)\/[A-Za-z0-9]+/
if figmaUrl AND NOT FIGMA_URL_PATTERN.test(figmaUrl):
  AskUserQuestion("Invalid Figma URL format. Please provide a valid Figma URL.")
  STOP

// readTalismanSection: "misc"
config = readTalismanSection("misc")
if NOT config?.design_sync?.enabled:
  AskUserQuestion("Design sync is disabled. Enable it in talisman.yml:\n\ndesign_sync:\n  enabled: true")
  STOP

// Step 4: Check Figma MCP availability
// Try calling figma_list_components — if MCP not available, degrade gracefully
figmaMcpAvailable = true  // set false if MCP call fails

// Step 5: Check agent-browser availability (for Phase 2.5)
agentBrowserAvailable = checkAgentBrowser()  // non-blocking, used later

// Step 6: Session isolation
CHOME = "${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
timestamp = Bash("date +%Y%m%d-%H%M%S").stdout.trim()
workDir = "tmp/design-sync/{timestamp}"
Bash("mkdir -p {workDir}/vsm {workDir}/components {workDir}/reviews {workDir}/iterations")

// Step 7: Write state file with session isolation
stateFile = "tmp/.rune-design-sync-{timestamp}.json"
Write(stateFile, JSON.stringify({
  status: "active",
  phase: "pre-flight",
  figma_url: figmaUrl,
  work_dir: workDir,
  config_dir: CHOME,
  owner_pid: "$PPID",
  session_id: "$CLAUDE_SESSION_ID",
  started_at: timestamp,
  flags: flags
}))

// Step 8: Handle flags
if flags.resumeWork:
  // Find most recent VSM directory
  // Resume from Phase 2
if flags.reviewOnly:
  // Skip to Phase 3
```

See [figma-url-parser.md](references/figma-url-parser.md) for URL format details.

## Phase 1: Design Extraction

Extract Figma design data and create Visual Spec Maps (VSM).

```
// Step 1: Create extraction team
TeamCreate("rune-design-sync-{timestamp}")

// Step 2: Create extraction tasks from Figma URL
// Parse Figma URL to identify target nodes
figmaData = figma_fetch_design(url=figmaUrl)
components = figma_list_components(url=figmaUrl)

// Step 3: Create one task per top-level component/frame
for each component in components:
  TaskCreate({
    subject: "Extract VSM for {component.name}",
    description: "Fetch Figma node {component.id}, extract tokens, build region tree, map variants. Output: {workDir}/vsm/{component.name}.md",
    metadata: { phase: "extraction", node_id: component.id }
  })

// Step 4: Summon design-sync-agent workers
maxWorkers = config?.design_sync?.max_extraction_workers ?? 2
for i in range(maxWorkers):
  Agent(team_name="rune-design-sync-{timestamp}", name="design-syncer-{i+1}", ...)
    // Spawn design-sync-agent with extraction context

// Step 5: Monitor until extraction complete
// Use TaskList polling (see polling-guard)
```

See [phase1-design-extraction.md](references/phase1-design-extraction.md) for the full extraction algorithm.

### VSM Output Format

See [vsm-spec.md](references/vsm-spec.md) for the complete Visual Spec Map schema.

## Phase 1.5: User Confirmation

```
if NOT flags.planOnly:
  // Show VSM summary to user
  vsmFiles = Glob("tmp/design-sync/{timestamp}/vsm/*.md")
  summary = generateVsmSummary(vsmFiles)
  AskUserQuestion("VSM extraction complete:\n\n{summary}\n\nProceed to implementation? [yes/edit/stop]")

if flags.planOnly:
  // Write completion report, cleanup team, STOP
  updateState({ status: "completed", phase: "plan-only" })
  STOP
```

## Phase 2: Implementation

Create components from VSM using swarm workers.

```
// Step 1: Parse VSM files into implementation tasks
vsmFiles = Glob("{workDir}/vsm/*.md")
for each vsm in vsmFiles:
  TaskCreate({
    subject: "Implement {component_name} from VSM",
    description: "Read VSM at {vsm.path}. Create component following design tokens, layout, variants, and a11y requirements.",
    metadata: { phase: "implementation", vsm_path: vsm.path }
  })

// Step 2: Summon rune-smith workers
maxWorkers = config?.design_sync?.max_implementation_workers ?? 3
for i in range(maxWorkers):
  Agent(team_name="rune-design-sync-{timestamp}", name="rune-smith-{i+1}", ...)
    // Spawn rune-smith with VSM context + frontend-design-patterns skill

// Step 3: Monitor until implementation complete
```

See [phase2-design-implementation.md](references/phase2-design-implementation.md) for implementation guidance.

## Phase 2.5: Design Iteration (Optional)

If agent-browser is available and design_sync.iterate_enabled is true:

```
if agentBrowserAvailable AND config?.design_sync?.iterate_enabled:
  // Create iteration tasks for each implemented component
  for each component in implementedComponents:
    TaskCreate({
      subject: "Iterate on {component_name} design fidelity",
      description: "Run screenshot→analyze→improve loop. Max {config.design_sync.max_iterations ?? 5} iterations.",
      metadata: { phase: "iteration", vsm_path: component.vsm_path }
    })

  // Summon design-iterator workers
  maxIterators = config?.design_sync?.max_iteration_workers ?? 2
  for i in range(maxIterators):
    Agent(team_name="rune-design-sync-{timestamp}", name="design-iter-{i+1}", ...)
      // Spawn design-iterator with VSM + screenshot context
```

See [screenshot-comparison.md](references/screenshot-comparison.md) for browser integration.

## Phase 3: Fidelity Review

Score implementation against design specifications.

```
// Step 1: Create fidelity review tasks
for each component in implementedComponents:
  TaskCreate({
    subject: "Review fidelity of {component_name}",
    description: "Score implementation against VSM. 6 dimensions: tokens, layout, responsive, a11y, variants, states.",
    metadata: { phase: "review", vsm_path: component.vsm_path }
  })

// Step 2: Summon design-implementation-reviewer
Agent(team_name="rune-design-sync-{timestamp}", name="design-reviewer-1", ...)
  // Spawn design-implementation-reviewer with VSM + component paths

// Step 3: Aggregate fidelity scores
// Read reviewer output, compute overall fidelity score
```

See [phase3-fidelity-review.md](references/phase3-fidelity-review.md) for the review protocol.
See [fidelity-scoring.md](references/fidelity-scoring.md) for the scoring algorithm.

## Phase 4: Cleanup

```javascript
// Step 1: Generate completion report
Write("{workDir}/report.md", completionReport)

// Step 2: Persist echoes
// Write design patterns learned to .claude/echoes/

// Step 3: Shutdown workers — dynamic member discovery with fallback
const teamName = `rune-design-sync-${timestamp}`
let allMembers = []
try {
  const CHOME = Bash(`echo "\${CLAUDE_CONFIG_DIR:-$HOME/.claude}"`).trim()
  const teamConfig = JSON.parse(Read(`${CHOME}/teams/${teamName}/config.json`))
  const members = Array.isArray(teamConfig.members) ? teamConfig.members : []
  allMembers = members.map(m => m.name).filter(n => n && /^[a-zA-Z0-9_-]+$/.test(n))
} catch (e) {
  // Fallback: known workers across all design-sync phases (max counts from talisman defaults)
  // Phase 1 (extraction): design-syncer-1, design-syncer-2
  // Phase 2 (implementation): rune-smith-1, rune-smith-2, rune-smith-3
  // Phase 3 (iteration): design-iter-1, design-iter-2, design-reviewer-1
  allMembers = ["design-syncer-1", "design-syncer-2",
    "rune-smith-1", "rune-smith-2", "rune-smith-3",
    "design-iter-1", "design-iter-2", "design-reviewer-1"]
}

for (const member of allMembers) {
  SendMessage({ type: "shutdown_request", recipient: member, content: "Design sync complete" })
}

// Grace period for shutdown acknowledgment
if (allMembers.length > 0) { Bash("sleep 15") }

// Step 4: Cleanup team — TeamDelete with retry-with-backoff (3 attempts: 0s, 5s, 10s)
let cleanupTeamDeleteSucceeded = false
const CLEANUP_DELAYS = [0, 5000, 10000]
for (let attempt = 0; attempt < CLEANUP_DELAYS.length; attempt++) {
  if (attempt > 0) Bash(`sleep ${CLEANUP_DELAYS[attempt] / 1000}`)
  try { TeamDelete(); cleanupTeamDeleteSucceeded = true; break } catch (e) {
    if (attempt === CLEANUP_DELAYS.length - 1) warn(`design-sync cleanup: TeamDelete failed after ${CLEANUP_DELAYS.length} attempts`)
  }
}
// Filesystem fallback — only if TeamDelete never succeeded (QUAL-012)
if (!cleanupTeamDeleteSucceeded) {
  Bash(`CHOME="\${CLAUDE_CONFIG_DIR:-$HOME/.claude}" && rm -rf "$CHOME/teams/${teamName}/" "$CHOME/tasks/${teamName}/" 2>/dev/null`)
  try { TeamDelete() } catch (e) { /* best effort — clear SDK leadership state */ }
}

// Step 5: Update state
updateState({ status: "completed", phase: "cleanup", fidelity_score: overallScore })

// Step 6: Report to user
"Design sync complete. Fidelity: {score}/100. Report: {workDir}/report.md"
```

## Configuration

```yaml
# talisman.yml
design_sync:
  enabled: false                         # Master toggle (default: false)
  max_extraction_workers: 2              # Extraction phase workers
  max_implementation_workers: 3          # Implementation phase workers
  max_iteration_workers: 2              # Iteration phase workers
  max_iterations: 5                      # Max design iterations per component
  iterate_enabled: false                 # Enable screenshot→fix loop (requires agent-browser)
  fidelity_threshold: 80                 # Min fidelity score to pass review
  token_snap_distance: 20               # Max RGB distance for color snapping
  figma_cache_ttl: 1800                  # Figma API cache TTL (seconds)
```

## State Persistence

All state files follow session isolation rules:

```json
{
  "status": "active",
  "phase": "extraction",
  "config_dir": "/Users/user/.claude",
  "owner_pid": "12345",
  "session_id": "abc-123",
  "started_at": "20260225-120000",
  "figma_url": "https://www.figma.com/design/...",
  "work_dir": "tmp/design-sync/20260225-120000",
  "components": [],
  "fidelity_scores": {}
}
```

## References

- [phase1-design-extraction.md](references/phase1-design-extraction.md) — Figma parsing and VSM creation
- [phase2-design-implementation.md](references/phase2-design-implementation.md) — VSM-guided implementation
- [phase3-fidelity-review.md](references/phase3-fidelity-review.md) — Fidelity review protocol
- [vsm-spec.md](references/vsm-spec.md) — Visual Spec Map schema
- [design-token-mapping.md](references/design-token-mapping.md) — Color snapping and token mapping
- [figma-url-parser.md](references/figma-url-parser.md) — URL format and file key extraction
- [fidelity-scoring.md](references/fidelity-scoring.md) — Scoring algorithm
- [screenshot-comparison.md](references/screenshot-comparison.md) — Agent-browser integration
