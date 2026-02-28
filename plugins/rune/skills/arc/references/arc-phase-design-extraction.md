# Phase 3: DESIGN EXTRACTION — Arc Design Sync Integration

Extracts Figma design specifications and creates Visual Spec Maps (VSM) for the arc pipeline.
Gated by `design_sync.enabled` in talisman. **Non-blocking** — design phases never halt the pipeline.

**Team**: `arc-design-{id}` (design-sync-agent workers)
**Tools**: Read, Write, Bash, Task, TaskCreate, TaskUpdate, TaskList, TeamCreate, SendMessage
**Timeout**: 10 min (PHASE_TIMEOUTS.design_extraction = 600_000)
**Inputs**: id, plan frontmatter (Figma URL), `arcConfig.design_sync` (resolved via `resolveArcConfig()`)
**Outputs**: `tmp/arc/{id}/vsm/` directory with VSM files per component
**Error handling**: Non-blocking. All design phases are skippable — failures set status "skipped" with reason.
**Consumers**: Phase 5.2 DESIGN VERIFICATION (reads VSM files), WORK phase workers (consult VSM for implementation)

> **Note**: `sha256()`, `updateCheckpoint()`, `exists()`, and `warn()` are dispatcher-provided utilities
> available in the arc orchestrator context. Phase reference files call these without import.

## Pre-checks

1. Skip gate — `arcConfig.design_sync?.enabled !== true` → skip
2. Extract Figma URL from plan frontmatter — skip if absent
3. Check Figma MCP tools available — skip with warning if unavailable
4. Validate Figma URL format: `/^https:\/\/www\.figma\.com\/(design|file)\/[A-Za-z0-9]+/`

## Algorithm

```javascript
updateCheckpoint({ phase: "design_extraction", status: "in_progress", phase_sequence: 5.1, team_name: null })

// 0. Skip gate — design sync is DISABLED by default (opt-in via talisman)
const designSyncConfig = arcConfig.design_sync ?? {}
const designSyncEnabled = designSyncConfig.enabled === true
if (!designSyncEnabled) {
  log("Design extraction skipped — design_sync.enabled is false in talisman.")
  updateCheckpoint({ phase: "design_extraction", status: "skipped" })
  return
}

// 1. Extract Figma URL from plan frontmatter
const planContent = Read(checkpoint.plan_file)
const figmaUrlMatch = planContent.match(/figma_url:\s*(https:\/\/www\.figma\.com\/[^\s]+)/)
const figmaUrl = figmaUrlMatch?.[1]

if (!figmaUrl) {
  log("Design extraction skipped — no figma_url found in plan frontmatter.")
  updateCheckpoint({ phase: "design_extraction", status: "skipped" })
  return
}

// 2. Validate Figma URL format
const FIGMA_URL_PATTERN = /^https:\/\/www\.figma\.com\/(design|file)\/[A-Za-z0-9]+/
if (!FIGMA_URL_PATTERN.test(figmaUrl)) {
  warn(`Design extraction: invalid Figma URL format: ${figmaUrl}`)
  updateCheckpoint({ phase: "design_extraction", status: "skipped" })
  return
}

// 3. Check Figma MCP availability (non-blocking probe)
let figmaMcpAvailable = false
try {
  // Probe: attempt a minimal MCP call — if it throws, MCP is unavailable
  figma_list_components({ url: figmaUrl })
  figmaMcpAvailable = true
} catch (e) {
  warn("Design extraction: Figma MCP tools unavailable. Skipping design extraction. Check .mcp.json configuration.")
  updateCheckpoint({ phase: "design_extraction", status: "skipped" })
  return
}

// 4. Prepare output directory
Bash(`mkdir -p "tmp/arc/${id}/vsm"`)

// 5. Create extraction team
prePhaseCleanup(checkpoint)
TeamCreate({ team_name: `arc-design-${id}` })

updateCheckpoint({
  phase: "design_extraction", status: "in_progress", phase_sequence: 5.1,
  team_name: `arc-design-${id}`,
  figma_url: figmaUrl
})

// 6. Fetch top-level components from Figma
const figmaData = figma_fetch_design({ url: figmaUrl })
const components = figma_list_components({ url: figmaUrl })
const maxWorkers = designSyncConfig.max_extraction_workers ?? 2

// 7. Create extraction tasks (one per component)
for (const component of components.slice(0, 20)) {  // cap at 20 components
  TaskCreate({
    subject: `Extract VSM for ${component.name}`,
    description: `Fetch Figma node ${component.id} from ${figmaUrl}. Extract design tokens, region tree, variant map. Output to: tmp/arc/${id}/vsm/${component.name}.json`,
    metadata: { phase: "extraction", node_id: component.id, figma_url: figmaUrl }
  })
}

// 8. Spawn design-sync-agent workers
for (let i = 0; i < Math.min(maxWorkers, components.length); i++) {
  Agent({
    subagent_type: "general-purpose", model: "sonnet",
    name: `design-syncer-${i + 1}`, team_name: `arc-design-${id}`,
    prompt: `You are design-syncer-${i + 1}. Extract Figma design specs and create VSM files.
      Figma URL: ${figmaUrl}
      Output directory: tmp/arc/${id}/vsm/
      [inject agent design-sync-agent.md content]`
  })
}

// 9. Monitor extraction
waitForCompletion([...Array(maxWorkers).keys()].map(i => `design-syncer-${i + 1}`), {
  timeoutMs: 480_000  // 8 min inner budget
})

// 10. Shutdown workers + cleanup team
for (let i = 0; i < maxWorkers; i++) {
  SendMessage({ type: "shutdown_request", recipient: `design-syncer-${i + 1}` })
}
sleep(15_000)

try {
  TeamDelete()
} catch (e) {
  const CHOME = process.env.CLAUDE_CONFIG_DIR || `${HOME}/.claude`
  Bash(`rm -rf "${CHOME}/teams/arc-design-${id}" "${CHOME}/tasks/arc-design-${id}" 2>/dev/null`)
}

// 11. Collect VSM output paths
const vsmFiles = Bash(`find "tmp/arc/${id}/vsm" -name "*.json" 2>/dev/null`).trim().split('\n').filter(Boolean)

updateCheckpoint({
  phase: "design_extraction", status: "completed",
  phase_sequence: 5.1, team_name: null,
  vsm_files: vsmFiles,
  vsm_count: vsmFiles.length,
  figma_url: figmaUrl
})
```

## Error Handling

| Error | Recovery |
|-------|----------|
| `design_sync.enabled` is false | Skip phase — status "skipped" |
| No Figma URL in plan frontmatter | Skip phase — status "skipped" |
| Figma MCP tools unavailable | Skip phase — status "skipped", warn user |
| Figma API timeout (>60s) | Retry once, then skip with warning |
| Agent failure | Skip phase — design phases are non-blocking |

## Crash Recovery

| Resource | Location |
|----------|----------|
| VSM files | `tmp/arc/{id}/vsm/*.json` |
| Team config | `$CHOME/teams/arc-design-{id}/` |
| Task list | `$CHOME/tasks/arc-design-{id}/` |
| Checkpoint state | `.claude/arc/{id}/checkpoint.json` (phase: "design_extraction") |

Recovery: On `--resume`, if design_extraction is `in_progress`, clean up stale team and re-run from the beginning. Extraction is idempotent — VSM files are overwritten cleanly.
