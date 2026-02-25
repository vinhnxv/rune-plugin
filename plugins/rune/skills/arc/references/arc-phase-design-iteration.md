# Phase 7.6: DESIGN_ITERATION — Full Algorithm

Iterative design refinement — runs a screenshot-analyze-improve loop to fix design fidelity gaps. Conditional phase — runs only when fidelity score is below threshold AND convergence has passed.

**Team**: `arc-design-iterate-{id}` (self-managed)
**Tools**: Read, Write, Edit, Bash, Glob, Grep (+ agent-browser if available)
**Timeout**: 10 min (talisman: `arc.timeouts.design_iteration`, default 600000ms)
**Inputs**: id, VSM files, design-verification.md (fidelity report), component files
**Outputs**: `tmp/arc/{id}/design-iteration.md` (iteration report)
**Error handling**: Non-blocking (WARN). Failed iteration doesn't halt pipeline.
**Consumers**: SKILL.md (Phase 7.6 stub)

> **Note**: `sha256()`, `updateCheckpoint()`, `exists()`, and `warn()` are dispatcher-provided utilities available in the arc orchestrator context.

## Algorithm

```javascript
// ═══════════════════════════════════════════════════════
// STEP 0: PRE-FLIGHT GUARDS
// ═══════════════════════════════════════════════════════

if (!/^[a-zA-Z0-9_-]+$/.test(id)) throw new Error(`Phase 7.6: unsafe id value: "${id}"`)

// Condition 1: design_verification completed
const verificationStatus = checkpoint.phases?.design_verification?.status
if (verificationStatus !== "completed") {
  updateCheckpoint({ phase: "design_iteration", status: "skipped", reason: "design_verification not completed" })
  return
}

// Condition 2: fidelity below threshold
const designConfig = talisman?.design_sync ?? {}
const fidelityThreshold = designConfig.fidelity_threshold ?? 80
const currentFidelity = checkpoint.phases?.design_verification?.fidelity_score ?? 0

if (currentFidelity >= fidelityThreshold) {
  updateCheckpoint({
    phase: "design_iteration", status: "skipped",
    reason: `fidelity ${currentFidelity} >= threshold ${fidelityThreshold}`
  })
  return  // Skip — already passing
}

// Condition 3: design_sync.iterate_enabled (optional gate)
// When false, skip iteration even if fidelity is low
if (designConfig.iterate_enabled === false) {
  warn(`Phase 7.6: fidelity ${currentFidelity} < ${fidelityThreshold} but iterate_enabled=false — skipping`)
  updateCheckpoint({ phase: "design_iteration", status: "skipped", reason: "iterate_enabled=false" })
  return
}

// Condition 4: convergence loop must have passed (post-mend)
// Prevents running iteration before code fixes are stable
const convergenceStatus = checkpoint.convergence?.status
if (convergenceStatus !== "converged" && convergenceStatus !== "max_cycles") {
  updateCheckpoint({ phase: "design_iteration", status: "skipped", reason: "convergence not reached" })
  return
}

const maxIterations = designConfig.max_iterations ?? 3
const vsmFiles = Glob(`tmp/arc/${id}/vsm/*.md`)

// ═══════════════════════════════════════════════════════
// STEP 1: IDENTIFY COMPONENTS NEEDING ITERATION
// ═══════════════════════════════════════════════════════

const componentScores = checkpoint.phases?.design_verification?.component_scores ?? {}
const componentsToIterate = Object.entries(componentScores)
  .filter(([_, score]) => score < fidelityThreshold)
  .sort(([_, a], [__, b]) => a - b)  // Lowest fidelity first

if (componentsToIterate.length === 0) {
  updateCheckpoint({ phase: "design_iteration", status: "skipped", reason: "no components below threshold" })
  return
}

// ═══════════════════════════════════════════════════════
// STEP 2: TEAM CREATION
// ═══════════════════════════════════════════════════════

prePhaseCleanup(checkpoint)
TeamCreate({ team_name: `arc-design-iterate-${id}` })
const phaseStart = Date.now()
const timeoutMs = designConfig.iteration_timeout ?? talisman?.arc?.timeouts?.design_iteration ?? 600_000

Bash(`mkdir -p "tmp/arc/${id}/design-iterations"`)

updateCheckpoint({
  phase: "design_iteration", status: "in_progress", phase_sequence: 7.6,
  team_name: `arc-design-iterate-${id}`,
  components_to_iterate: componentsToIterate.length,
  max_iterations: maxIterations
})

// ═══════════════════════════════════════════════════════
// STEP 3: CREATE ITERATION TASKS
// ═══════════════════════════════════════════════════════

for (const [componentName, currentScore] of componentsToIterate) {
  const vsmPath = vsmFiles.find(f => f.includes(componentName))
  if (!vsmPath) {
    warn(`Phase 7.6: No VSM found for ${componentName} — skipping`)
    continue
  }

  const reviewPath = `tmp/arc/${id}/design-reviews/${componentName}.md`
  TaskCreate({
    subject: `Iterate on ${componentName} (fidelity: ${currentScore}/${fidelityThreshold})`,
    activeForm: `Iterating on ${componentName} design fidelity`,
    description: `Run screenshot→analyze→improve loop on ${componentName}.
      VSM: ${vsmPath}
      Previous review: ${reviewPath}
      Max iterations: ${maxIterations}
      Target fidelity: ${fidelityThreshold}
      Current fidelity: ${currentScore}
      Output: tmp/arc/${id}/design-iterations/${componentName}.md
      One change per iteration. Verify improvement. Revert on regression.
      Read design-sync/references/fidelity-scoring.md for scoring.`,
    metadata: {
      phase: "iteration",
      vsm_path: vsmPath,
      component: componentName,
      current_score: currentScore,
      target_score: fidelityThreshold
    }
  })
}

// ═══════════════════════════════════════════════════════
// STEP 4: SUMMON DESIGN ITERATORS
// ═══════════════════════════════════════════════════════

const maxWorkers = designConfig.max_iteration_workers ?? 2
const workersToSpawn = Math.min(maxWorkers, componentsToIterate.length)

for (let i = 0; i < workersToSpawn; i++) {
  Task({
    subagent_type: "general-purpose", model: "sonnet",
    name: `design-iter-${i + 1}`, team_name: `arc-design-iterate-${id}`,
    prompt: `You are design-iter-${i + 1}. Iteratively refine component implementations to match VSM specs.
      Max iterations per component: ${maxIterations}
      Target fidelity: ${fidelityThreshold}
      Output directory: tmp/arc/${id}/design-iterations/
      [inject agent work/design-iterator.md content]
      [inject skill frontend-design-patterns/SKILL.md content]

      GLYPH BUDGET PROTOCOL:
      Write ALL iteration details to output files.
      Return ONLY: file path + 1-sentence summary (max 50 words).`
  })
}

// ═══════════════════════════════════════════════════════
// STEP 5: MONITOR ITERATION
// ═══════════════════════════════════════════════════════

const workerNames = Array.from({ length: workersToSpawn }, (_, i) => `design-iter-${i + 1}`)
waitForCompletion(workerNames, { timeoutMs })

// ═══════════════════════════════════════════════════════
// STEP 6: AGGREGATE ITERATION RESULTS
// ═══════════════════════════════════════════════════════

const iterationFiles = Glob(`tmp/arc/${id}/design-iterations/*.md`)
let totalIterations = 0
let p1Fixed = 0
let p2Fixed = 0
const updatedScores = {}

for (const iterFile of iterationFiles) {
  const content = Read(iterFile)
  const componentName = iterFile.replace(/.*\//, '').replace('.md', '')

  // Extract iteration count
  const iterMatch = content.match(/Iterations:\s*(\d+)/)
  totalIterations += iterMatch ? parseInt(iterMatch[1]) : 0

  // Extract final fidelity (if reported)
  const scoreMatch = content.match(/Final [Ff]idelity:\s*(\d+)/)
  updatedScores[componentName] = scoreMatch ? parseInt(scoreMatch[1]) : componentScores[componentName]

  // Count fixed findings
  const p1Match = content.match(/P1 fixed:\s*(\d+)/)
  const p2Match = content.match(/P2 fixed:\s*(\d+)/)
  p1Fixed += p1Match ? parseInt(p1Match[1]) : 0
  p2Fixed += p2Match ? parseInt(p2Match[1]) : 0
}

const updatedOverall = Object.values(updatedScores).length > 0
  ? Math.round(Object.values(updatedScores).reduce((a, b) => a + b, 0) / Object.values(updatedScores).length)
  : currentFidelity

// ═══════════════════════════════════════════════════════
// STEP 7: WRITE ITERATION REPORT
// ═══════════════════════════════════════════════════════

const report = `# Design Iteration Report

**Before: ${currentFidelity}/100 → After: ${updatedOverall}/100**
**Total Iterations: ${totalIterations}**
**P1 Fixed: ${p1Fixed} | P2 Fixed: ${p2Fixed}**
**Verdict: ${updatedOverall >= fidelityThreshold ? 'PASS' : 'BELOW_THRESHOLD'}**

## Per-Component Results

| Component | Before | After | Iterations | Status |
|-----------|--------|-------|-----------|--------|
${Object.entries(updatedScores).map(([name, score]) =>
  `| ${name} | ${componentScores[name] ?? '?'} | ${score} | — | ${score >= fidelityThreshold ? 'PASS' : 'NEEDS_WORK'} |`
).join('\n')}

## Detail Reports

${iterationFiles.map(f => `- [${f.replace(/.*\//, '')}](${f})`).join('\n')}

<!-- SEAL: design-iteration-complete -->
`

Write(`tmp/arc/${id}/design-iteration.md`, report)

// ═══════════════════════════════════════════════════════
// STEP 8: CLEANUP
// ═══════════════════════════════════════════════════════

for (let i = 0; i < workersToSpawn; i++) {
  SendMessage({ type: "shutdown_request", recipient: `design-iter-${i + 1}` })
}
sleep(15_000)

try {
  TeamDelete()
} catch (e) {
  const CHOME = process.env.CLAUDE_CONFIG_DIR || `${HOME}/.claude`
  Bash(`rm -rf "${CHOME}/teams/arc-design-iterate-${id}" "${CHOME}/tasks/arc-design-iterate-${id}" 2>/dev/null`)
}

updateCheckpoint({
  phase: "design_iteration", status: "completed",
  artifact: `tmp/arc/${id}/design-iteration.md`,
  artifact_hash: sha256(Read(`tmp/arc/${id}/design-iteration.md`)),
  phase_sequence: 7.6,
  team_name: `arc-design-iterate-${id}`,
  fidelity_before: currentFidelity,
  fidelity_after: updatedOverall,
  total_iterations: totalIterations,
  p1_fixed: p1Fixed,
  p2_fixed: p2Fixed
})
```

## Phase Ordering

Design iteration runs AFTER convergence (review-mend loop) but BEFORE test:

```
... → Phase 7.5 VERIFY_MEND (convergence) → Phase 7.6 DESIGN_ITERATION → Phase 7.7 TEST → ...
```

This ordering ensures:
1. Code-level fixes are stable before visual refinement
2. Visual fixes are included in the test phase
3. Iteration doesn't fight with mend fixes on the same files

## Crash Recovery

| Resource | Location |
|----------|----------|
| Team config | `$CHOME/teams/arc-design-iterate-{id}/` |
| Task list | `$CHOME/tasks/arc-design-iterate-{id}/` |
| Iteration files | `tmp/arc/{id}/design-iterations/` |
| Iteration report | `tmp/arc/{id}/design-iteration.md` |

Recovery: `prePhaseCleanup()` handles team eviction. Iteration files persist on disk.
