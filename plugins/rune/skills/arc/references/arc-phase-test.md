# Phase 7.7: TEST — Full Algorithm

3-tier QA gate on converged code: unit → integration → E2E/browser.

**Team**: `arc-test-{id}` (self-managed)
**Tools**: Read, Glob, Grep, Bash (+ agent-browser via Bash for E2E)
**Timeout**: Dynamic — 15 min without E2E (inner 10m + 5m setup), 40 min with E2E (inner 35m + 5m setup)
**Inputs**: id, converged code on feature branch, enriched-plan.md, gap-analysis.md, resolution-report.md
**Outputs**: `tmp/arc/{id}/test-report.md` + screenshots in `tmp/arc/{id}/screenshots/`
**Error handling**: Non-blocking (WARN). Test results feed into audit but never halt pipeline.
**Consumers**: SKILL.md (Phase 7.7 stub)

> **Note**: `sha256()`, `updateCheckpoint()`, `exists()`, and `warn()` are dispatcher-provided utilities available in the arc orchestrator context. Phase reference files call these without import.

## Model Routing (Strict Enforcement)

| Role | Model | When |
|------|-------|------|
| Orchestration (STEP 0-4, 9-10) | Opus (team lead) | Always |
| Test strategy (STEP 1.5) | Opus (team lead) | Always |
| Unit test runner | Sonnet | STEP 5 |
| Integration test runner | Sonnet | STEP 6 |
| E2E browser tester | Sonnet | STEP 7 |
| Failure analyst | Opus (inherit) | STEP 8, only if failures |

Team lead NEVER runs `agent-browser` CLI or test commands directly.

## Algorithm

```javascript
// ═══════════════════════════════════════════════════════
// STEP 0: PRE-FLIGHT GUARDS
// ═══════════════════════════════════════════════════════

const noTestFlag = checkpoint.flags?.no_test === true
if (noTestFlag) {
  Write(`tmp/arc/${id}/test-report.md`, "Phase 7.7 skipped: --no-test flag set.\n<!-- SEAL: test-report-complete -->")
  updateCheckpoint({ phase: "test", status: "skipped" })
  return
}

const diffFiles = Bash("git diff --name-only main...HEAD").trim().split('\n').filter(Boolean)
if (diffFiles.length === 0) {
  Write(`tmp/arc/${id}/test-report.md`, "Phase 7.7 skipped: No changed files.\n<!-- SEAL: test-report-complete -->")
  updateCheckpoint({ phase: "test", status: "skipped" })
  return
}

// Read talisman testing config
const testingConfig = talisman?.testing ?? { enabled: true }
if (testingConfig.enabled === false) {
  Write(`tmp/arc/${id}/test-report.md`, "Phase 7.7 skipped: testing.enabled=false in talisman.\n<!-- SEAL: test-report-complete -->")
  updateCheckpoint({ phase: "test", status: "skipped" })
  return
}

// ═══════════════════════════════════════════════════════
// STEP 1: SCOPE DETECTION
// ═══════════════════════════════════════════════════════

// Classify files via Rune Gaze (backend/frontend/config/test)
// Cap at top 50 changed files for classification
const filesToClassify = diffFiles.slice(0, 50)
const backendExts = talisman?.['rune-gaze']?.backend_extensions ?? ['.py', '.go', '.rs', '.rb']
const frontendExts = talisman?.['rune-gaze']?.frontend_extensions ?? ['.tsx', '.ts', '.jsx']

const backendFiles = filesToClassify.filter(f => backendExts.some(e => f.endsWith(e)))
const frontendFiles = filesToClassify.filter(f =>
  frontendExts.some(e => f.endsWith(e)) && !f.includes('test') && !f.includes('spec')
)
const testFiles = filesToClassify.filter(f => f.includes('test') || f.includes('spec'))
const has_frontend = frontendFiles.length > 0

// Determine active tiers
const unitEnabled = testingConfig.tiers?.unit?.enabled !== false
const integrationEnabled = testingConfig.tiers?.integration?.enabled !== false
const e2eEnabled = testingConfig.tiers?.e2e?.enabled !== false && has_frontend
const testTiersActive = unitEnabled || integrationEnabled || e2eEnabled

if (!testTiersActive) {
  Write(`tmp/arc/${id}/test-report.md`, "Phase 7.7 skipped: No testable changes detected.\n<!-- SEAL: test-report-complete -->")
  updateCheckpoint({ phase: "test", status: "skipped" })
  return
}

// Compute test/implementation ratio
const uncoveredImplementations = backendFiles.filter(f => {
  // Check if corresponding test file exists
  const testVariants = generateTestPaths(f)  // from test-discovery.md algorithm
  return !testVariants.some(t => exists(t))
})

// ═══════════════════════════════════════════════════════
// STEP 1.5: TEST STRATEGY GENERATION
// ═══════════════════════════════════════════════════════

// Team lead (Opus) generates strategy document BEFORE any test execution
// Strategy is the instruction document for all downstream test runners
const strategy = generateTestStrategy({
  diffFiles, backendFiles, frontendFiles, testFiles,
  has_frontend, enrichedPlan: Read(`tmp/arc/${id}/enriched-plan.md`),
  tiers: { unit: unitEnabled, integration: integrationEnabled, e2e: e2eEnabled },
  uncoveredImplementations
})
Write(`tmp/arc/${id}/test-strategy.md`, strategy)

// ═══════════════════════════════════════════════════════
// STEP 2: TEST DISCOVERY
// ═══════════════════════════════════════════════════════

// See testing/references/test-discovery.md for full algorithm
const unitTests = discoverUnitTests(diffFiles)   // file-path heuristic
const integrationTests = discoverIntegrationTests(diffFiles)  // directory scan
const e2eRoutes = has_frontend ? discoverE2ERoutes(frontendFiles) : []

// ═══════════════════════════════════════════════════════
// STEP 3: SERVICE STARTUP (conditional)
// ═══════════════════════════════════════════════════════

// See testing/references/service-startup.md for full protocol
let servicesHealthy = false
if (integrationEnabled || e2eEnabled) {
  servicesHealthy = startServices(testingConfig)
  // If health check fails → skip integration/E2E, unit still runs
  if (!servicesHealthy) {
    warn("Services not healthy — skipping integration/E2E tiers")
  }
  Bash(`mkdir -p tmp/arc/${id}/screenshots/`)
}

// ═══════════════════════════════════════════════════════
// STEP 4: TEAM CREATION
// ═══════════════════════════════════════════════════════

prePhaseCleanup(checkpoint)  // Evict stale arc-test-{id} teams (EC-4.2)
TeamCreate({ team_name: `arc-test-${id}` })
const phaseStart = Date.now()
const innerBudget = has_frontend ? 2_100_000 : 600_000  // 35m with E2E, 10m without
function remainingBudget() { return innerBudget - (Date.now() - phaseStart) }

updateCheckpoint({
  phase: "test", status: "active", phase_sequence: 7.7,
  team_name: `arc-test-${id}`,
  tiers_run: [], pass_rate: null, coverage_pct: null, has_frontend
})

// ═══════════════════════════════════════════════════════
// STEP 5: TIER 1 — UNIT TESTS
// ═══════════════════════════════════════════════════════

if (unitEnabled && unitTests.length > 0) {
  // Spawn unit-test-runner teammate (Sonnet)
  Task({
    subagent_type: "general-purpose", model: "sonnet",
    name: "unit-test-runner", team_name: `arc-test-${id}`,
    prompt: `You are unit-test-runner. Run these unit tests: ${unitTests.join(', ')}
      Output to: tmp/arc/${id}/test-results-unit.md
      Strategy: ${Read(`tmp/arc/${id}/test-strategy.md`)}
      [inject agent unit-test-runner.md content]`
  })
  waitForCompletion(["unit-test-runner"], {
    timeoutMs: Math.min(180_000, remainingBudget())
  })
}

// ═══════════════════════════════════════════════════════
// STEP 6: TIER 2 — INTEGRATION TESTS (after unit)
// ═══════════════════════════════════════════════════════

if (integrationEnabled && servicesHealthy && integrationTests.length > 0) {
  Task({
    subagent_type: "general-purpose", model: "sonnet",
    name: "integration-test-runner", team_name: `arc-test-${id}`,
    prompt: `You are integration-test-runner. Run integration tests.
      Output to: tmp/arc/${id}/test-results-integration.md
      Strategy: ${Read(`tmp/arc/${id}/test-strategy.md`)}
      [inject agent integration-test-runner.md content]`
  })
  waitForCompletion(["integration-test-runner"], {
    timeoutMs: Math.min(240_000, remainingBudget())
  })
}

// ═══════════════════════════════════════════════════════
// STEP 7: TIER 3 — E2E/BROWSER TESTS (after integration)
// ═══════════════════════════════════════════════════════

const agentBrowserAvailable = Bash("agent-browser --version 2>/dev/null && echo 'yes' || echo 'no'").trim() === "yes"

if (e2eEnabled && servicesHealthy && agentBrowserAvailable && e2eRoutes.length > 0) {
  const maxRoutes = testingConfig.tiers?.e2e?.max_routes ?? 3
  const routesToTest = e2eRoutes.slice(0, maxRoutes)
  const baseUrl = testingConfig.tiers?.e2e?.base_url ?? "http://localhost:3000"

  // URL scope restriction (T10): reject non-localhost URLs
  const urlHost = new URL(baseUrl).hostname
  if (urlHost !== 'localhost' && urlHost !== '127.0.0.1') {
    warn(`E2E base_url ${baseUrl} is not localhost — restricting to prevent external navigation`)
  }

  // BROWSER ISOLATION: ALL browser work on dedicated Sonnet teammate
  Task({
    subagent_type: "general-purpose", model: "sonnet",
    name: "e2e-browser-tester", team_name: `arc-test-${id}`,
    prompt: `You are e2e-browser-tester. Test these routes: ${routesToTest.join(', ')}
      Base URL: ${baseUrl}
      Session: --session arc-e2e-${id}
      Output per route to: tmp/arc/${id}/e2e-route-{N}-result.md
      Aggregate to: tmp/arc/${id}/test-results-e2e.md
      Screenshots to: tmp/arc/${id}/screenshots/
      Strategy: ${Read(`tmp/arc/${id}/test-strategy.md`)}
      [inject agent-browser skill content]
      [inject agent e2e-browser-tester.md content]`
  })

  const e2eTimeout = (testingConfig.tiers?.e2e?.timeout ?? 300) * routesToTest.length * 1000
  waitForCompletion(["e2e-browser-tester"], {
    timeoutMs: Math.min(e2eTimeout + 60_000, remainingBudget())
  })
} else if (e2eEnabled && !agentBrowserAvailable) {
  warn("agent-browser not installed — skipping E2E tier. Install: npm i -g @anthropic-ai/agent-browser")
}

// ═══════════════════════════════════════════════════════
// STEP 8: FAILURE ANALYSIS (conditional — Opus, 3-min deadline)
// ═══════════════════════════════════════════════════════

const hasFailures = checkForFailures(`tmp/arc/${id}/test-results-*.md`)

if (hasFailures && remainingBudget() > 180_000) {
  Task({
    subagent_type: "general-purpose",  // inherits Opus from team lead
    name: "test-failure-analyst", team_name: `arc-test-${id}`,
    prompt: `You are test-failure-analyst. Analyze failures in:
      - tmp/arc/${id}/test-results-unit.md
      - tmp/arc/${id}/test-results-integration.md
      - tmp/arc/${id}/test-results-e2e.md
      Truncate input: first 200 + last 50 lines per file.
      Hard deadline: 3 minutes.
      [inject agent test-failure-analyst.md content]`
  })
  waitForCompletion(["test-failure-analyst"], {
    timeoutMs: Math.min(180_000, remainingBudget())
  })
}

// ═══════════════════════════════════════════════════════
// STEP 9: GENERATE TEST REPORT
// ═══════════════════════════════════════════════════════

// Reserve last 60s for STEPS 9-10
// Aggregate per-tier files (authoritative — NOT checkpoint files)
// See testing/references/test-report-template.md for format
const report = aggregateTestReport({
  id, tiersRun: activeTiers,
  unitResults: exists(`tmp/arc/${id}/test-results-unit.md`) ? Read(`tmp/arc/${id}/test-results-unit.md`) : null,
  integrationResults: exists(`tmp/arc/${id}/test-results-integration.md`) ? Read(`tmp/arc/${id}/test-results-integration.md`) : null,
  e2eResults: exists(`tmp/arc/${id}/test-results-e2e.md`) ? Read(`tmp/arc/${id}/test-results-e2e.md`) : null,
  strategy: Read(`tmp/arc/${id}/test-strategy.md`),
  uncoveredImplementations
})

Write(`tmp/arc/${id}/test-report.md`, report + "\n<!-- SEAL: test-report-complete -->")

// ═══════════════════════════════════════════════════════
// STEP 10: CLEANUP (correct ordering — prevents deadlocks)
// ═══════════════════════════════════════════════════════

// 1. Shutdown teammates FIRST (30s max wait)
SendMessage({ type: "shutdown_request", recipient: "unit-test-runner" })
SendMessage({ type: "shutdown_request", recipient: "integration-test-runner" })
SendMessage({ type: "shutdown_request", recipient: "e2e-browser-tester" })
SendMessage({ type: "shutdown_request", recipient: "test-failure-analyst" })
sleep(30_000)  // Wait for shutdown acknowledgment

// 2. Close browser sessions (teammates already closed)
Bash(`agent-browser session list 2>/dev/null | grep "arc-e2e-${id}" && agent-browser close --session arc-e2e-${id} 2>/dev/null || true`)

// 3. Stop Docker
if (dockerStarted) {
  Bash(`docker compose down --timeout 10 --remove-orphans 2>/dev/null || true`)
  // Fallback: kill by container IDs
  if (exists(`tmp/arc/${id}/docker-containers.json`)) {
    Bash(`docker kill $(jq -r '.[].ID' tmp/arc/${id}/docker-containers.json) 2>/dev/null || true`)
  }
}

// 4. TeamDelete with rm-rf fallback
try {
  TeamDelete()
} catch (e) {
  const CHOME = process.env.CLAUDE_CONFIG_DIR || `${HOME}/.claude`
  Bash(`rm -rf "${CHOME}/teams/arc-test-${id}" "${CHOME}/tasks/arc-test-${id}" 2>/dev/null`)
}

// 5. Update checkpoint
updateCheckpoint({
  phase: "test", status: "completed",
  artifact: `tmp/arc/${id}/test-report.md`,
  artifact_hash: sha256(Read(`tmp/arc/${id}/test-report.md`)),
  phase_sequence: 7.7,
  team_name: `arc-test-${id}`,
  tiers_run: activeTiers,
  pass_rate: computePassRate(report),
  coverage_pct: computeDiffCoverage(report),
  has_frontend
})
```

## Crash Recovery

If this phase crashes before cleanup:

| Resource | Location |
|----------|----------|
| Team config | `~/.claude/teams/arc-test-{id}/` |
| Task list | `~/.claude/tasks/arc-test-{id}/` |
| Browser sessions | `arc-e2e-{id}` (check `agent-browser session list`) |
| Docker containers | `tmp/arc/{id}/docker-containers.json` |
| Screenshots | `tmp/arc/{id}/screenshots/` |

Recovery: `prePhaseCleanup()` handles team/task cleanup. Docker containers auto-stop on Docker daemon restart. Browser sessions time out after 5 minutes of inactivity.
