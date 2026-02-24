# Phase 3: DESIGN_EXTRACTION — Full Algorithm

Figma design data extraction and Visual Spec Map (VSM) creation. Conditional phase — runs only when `design_sync.enabled` AND a Figma URL is present in the plan.

**Team**: `arc-design-extract-{id}` (self-managed)
**Tools**: Read, Write, Bash, Glob, Grep (+ Figma MCP tools via design-sync-agent)
**Timeout**: 5 min (talisman: `arc.timeouts.design_extraction`, default 300000ms)
**Inputs**: id, enriched-plan.md, Figma URL from plan metadata
**Outputs**: `tmp/arc/{id}/design-extraction.md` (summary) + `tmp/arc/{id}/vsm/` (VSM files)
**Error handling**: Non-blocking (WARN). Missing VSM degrades to code-only review in Phase 5.2.
**Consumers**: SKILL.md (Phase 3 stub), Phase 5.2 DESIGN_VERIFICATION, Phase 7.6 DESIGN_ITERATION

> **Note**: `sha256()`, `updateCheckpoint()`, `exists()`, and `warn()` are dispatcher-provided utilities available in the arc orchestrator context. Phase reference files call these without import.

## Algorithm

```javascript
// ═══════════════════════════════════════════════════════
// STEP 0: PRE-FLIGHT GUARDS
// ═══════════════════════════════════════════════════════

// Defense-in-depth: id validated at arc init — re-assert here
if (!/^[a-zA-Z0-9_-]+$/.test(id)) throw new Error(`Phase 3: unsafe id value: "${id}"`)

// Condition 1: design_sync.enabled
const designConfig = talisman?.design_sync ?? { enabled: false }
if (!designConfig.enabled) {
  updateCheckpoint({ phase: "design_extraction", status: "skipped", reason: "design_sync.enabled=false" })
  return  // Skip silently
}

// Condition 2: Figma URL present in plan
const plan = Read(`tmp/arc/${id}/enriched-plan.md`)
const FIGMA_URL_PATTERN = /https:\/\/www\.figma\.com\/(design|file)\/[A-Za-z0-9]+[^\s)"]*/
const figmaMatch = plan.match(FIGMA_URL_PATTERN)

if (!figmaMatch) {
  updateCheckpoint({ phase: "design_extraction", status: "skipped", reason: "no Figma URL in plan" })
  return  // Skip silently
}

const figmaUrl = figmaMatch[0]

// Validate URL structure before any MCP calls
if (!/^https:\/\/www\.figma\.com\/(design|file)\/[A-Za-z0-9]+(\/[^?]*)?(\?.*)?$/.test(figmaUrl)) {
  warn(`Phase 3: Figma URL failed validation: ${figmaUrl}`)
  updateCheckpoint({ phase: "design_extraction", status: "skipped", reason: "invalid Figma URL format" })
  return
}

// ═══════════════════════════════════════════════════════
// STEP 1: SETUP
// ═══════════════════════════════════════════════════════

Bash(`mkdir -p "tmp/arc/${id}/vsm"`)

// ═══════════════════════════════════════════════════════
// STEP 2: TEAM CREATION
// ═══════════════════════════════════════════════════════

prePhaseCleanup(checkpoint)  // Evict stale arc-design-extract-{id} teams
TeamCreate({ team_name: `arc-design-extract-${id}` })
const phaseStart = Date.now()
const timeoutMs = designConfig.extraction_timeout ?? talisman?.arc?.timeouts?.design_extraction ?? 300_000

updateCheckpoint({
  phase: "design_extraction", status: "in_progress", phase_sequence: 3,
  team_name: `arc-design-extract-${id}`,
  figma_url: figmaUrl
})

// ═══════════════════════════════════════════════════════
// STEP 3: CREATE EXTRACTION TASKS
// ═══════════════════════════════════════════════════════

// Single task for extraction (design-sync-agent handles internal decomposition)
TaskCreate({
  subject: `Extract VSM from Figma: ${figmaUrl}`,
  description: `Fetch Figma design data from ${figmaUrl}.
    Extract design tokens, region trees, variant maps, responsive specs.
    Write VSM files to: tmp/arc/${id}/vsm/
    Write summary to: tmp/arc/${id}/design-extraction.md
    Follow the VSM schema (vsm_schema_version: "1.0").
    Read design-sync/references/vsm-spec.md for the schema.
    Read design-sync/references/phase1-design-extraction.md for the algorithm.`,
  metadata: { phase: "extraction", figma_url: figmaUrl }
})

// ═══════════════════════════════════════════════════════
// STEP 4: SUMMON EXTRACTION AGENT
// ═══════════════════════════════════════════════════════

const maxWorkers = designConfig.max_extraction_workers ?? 2

for (let i = 0; i < maxWorkers; i++) {
  Task({
    subagent_type: "general-purpose", model: "sonnet",
    name: `design-syncer-${i + 1}`, team_name: `arc-design-extract-${id}`,
    prompt: `You are design-syncer-${i + 1}. Extract Figma design specs and create VSM files.
      Figma URL: ${figmaUrl}
      Output directory: tmp/arc/${id}/vsm/
      Summary output: tmp/arc/${id}/design-extraction.md
      [inject agent work/design-sync-agent.md content]
      [inject skill design-sync/references/vsm-spec.md content]
      [inject skill design-sync/references/phase1-design-extraction.md content]`
  })
}

// ═══════════════════════════════════════════════════════
// STEP 5: MONITOR EXTRACTION
// ═══════════════════════════════════════════════════════

waitForCompletion(
  Array.from({ length: maxWorkers }, (_, i) => `design-syncer-${i + 1}`),
  { timeoutMs }
)

// ═══════════════════════════════════════════════════════
// STEP 6: VALIDATE OUTPUT
// ═══════════════════════════════════════════════════════

const vsmFiles = Glob(`tmp/arc/${id}/vsm/*.md`)
const extractionReport = exists(`tmp/arc/${id}/design-extraction.md`)

if (vsmFiles.length === 0) {
  warn("Phase 3: No VSM files produced — design extraction failed")
  Write(`tmp/arc/${id}/design-extraction.md`,
    "Phase 3 DESIGN_EXTRACTION: No VSM files produced. Extraction failed.\n" +
    `Figma URL: ${figmaUrl}\n<!-- SEAL: design-extraction-complete -->`)
}

// ═══════════════════════════════════════════════════════
// STEP 7: CLEANUP
// ═══════════════════════════════════════════════════════

// Shutdown workers
for (let i = 0; i < maxWorkers; i++) {
  SendMessage({ type: "shutdown_request", recipient: `design-syncer-${i + 1}` })
}
sleep(15_000)

// TeamDelete with rm-rf fallback
try {
  TeamDelete()
} catch (e) {
  const CHOME = process.env.CLAUDE_CONFIG_DIR || `${HOME}/.claude`
  Bash(`rm -rf "${CHOME}/teams/arc-design-extract-${id}" "${CHOME}/tasks/arc-design-extract-${id}" 2>/dev/null`)
}

// Update checkpoint
updateCheckpoint({
  phase: "design_extraction", status: "completed",
  artifact: `tmp/arc/${id}/design-extraction.md`,
  artifact_hash: exists(`tmp/arc/${id}/design-extraction.md`)
    ? sha256(Read(`tmp/arc/${id}/design-extraction.md`)) : null,
  phase_sequence: 3,
  team_name: `arc-design-extract-${id}`,
  vsm_count: vsmFiles.length,
  figma_url: figmaUrl
})
```

## Crash Recovery

| Resource | Location |
|----------|----------|
| Team config | `$CHOME/teams/arc-design-extract-{id}/` (where `CHOME="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"`) |
| Task list | `$CHOME/tasks/arc-design-extract-{id}/` |
| VSM files | `tmp/arc/{id}/vsm/` |
| Extraction report | `tmp/arc/{id}/design-extraction.md` |

Recovery: `prePhaseCleanup()` handles team/task eviction. VSM files persist on disk for resume.
