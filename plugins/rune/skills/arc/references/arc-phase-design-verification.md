# Phase 5.2: DESIGN_VERIFICATION — Full Algorithm

Design fidelity review — scores implementation accuracy against Visual Spec Maps (VSM). Conditional phase — runs only when design_extraction phase completed with VSM files.

**Team**: `arc-design-verify-{id}` (self-managed)
**Tools**: Read, Glob, Grep (read-only — reviewer does not write implementation code)
**Timeout**: 5 min (talisman: `arc.timeouts.design_verification`, default 300000ms)
**Inputs**: id, VSM files from Phase 3, implemented component files
**Outputs**: `tmp/arc/{id}/design-verification.md` (fidelity report with scores)
**Error handling**: Non-blocking (WARN). Missing fidelity score defaults to 0, triggering Phase 7.6.
**Consumers**: SKILL.md (Phase 5.2 stub), Phase 7.6 DESIGN_ITERATION

> **Note**: `sha256()`, `updateCheckpoint()`, `exists()`, and `warn()` are dispatcher-provided utilities available in the arc orchestrator context.

## Algorithm

```javascript
// ═══════════════════════════════════════════════════════
// STEP 0: PRE-FLIGHT GUARDS
// ═══════════════════════════════════════════════════════

if (!/^[a-zA-Z0-9_-]+$/.test(id)) throw new Error(`Phase 5.2: unsafe id value: "${id}"`)

// Condition: design_extraction phase completed with VSM output
const designExtractionStatus = checkpoint.phases?.design_extraction?.status
if (designExtractionStatus !== "completed") {
  updateCheckpoint({ phase: "design_verification", status: "skipped", reason: "design_extraction not completed" })
  return  // Skip silently
}

const vsmFiles = Glob(`tmp/arc/${id}/vsm/*.md`)
if (vsmFiles.length === 0) {
  updateCheckpoint({ phase: "design_verification", status: "skipped", reason: "no VSM files found" })
  return  // Skip silently
}

// Read talisman config
const designConfig = talisman?.design_sync ?? {}
const fidelityThreshold = designConfig.fidelity_threshold ?? 80

// ═══════════════════════════════════════════════════════
// STEP 1: TEAM CREATION
// ═══════════════════════════════════════════════════════

prePhaseCleanup(checkpoint)
TeamCreate({ team_name: `arc-design-verify-${id}` })
const phaseStart = Date.now()
const timeoutMs = designConfig.verification_timeout ?? talisman?.arc?.timeouts?.design_verification ?? 300_000

Bash(`mkdir -p "tmp/arc/${id}/design-reviews"`)

updateCheckpoint({
  phase: "design_verification", status: "in_progress", phase_sequence: 5.2,
  team_name: `arc-design-verify-${id}`,
  vsm_count: vsmFiles.length
})

// ═══════════════════════════════════════════════════════
// STEP 2: CREATE REVIEW TASKS
// ═══════════════════════════════════════════════════════

// One review task per VSM file
for (const vsm of vsmFiles) {
  const componentName = vsm.replace(/.*\//, '').replace('.md', '')
  TaskCreate({
    subject: `Review fidelity: ${componentName}`,
    activeForm: `Reviewing fidelity of ${componentName}`,
    description: `Score implementation of ${componentName} against VSM at ${vsm}.
      6 dimensions: token compliance, layout fidelity, responsive coverage, accessibility, variant completeness, state coverage.
      Write output to: tmp/arc/${id}/design-reviews/${componentName}.md
      Use FIDE-NNN finding prefix. Classify P1/P2/P3.
      Read design-sync/references/fidelity-scoring.md for scoring algorithm.`,
    metadata: { phase: "verification", vsm_path: vsm, component: componentName }
  })
}

// ═══════════════════════════════════════════════════════
// STEP 3: SUMMON REVIEWER
// ═══════════════════════════════════════════════════════

Task({
  subagent_type: "general-purpose", model: "sonnet",
  name: "design-reviewer-1", team_name: `arc-design-verify-${id}`,
  prompt: `You are design-reviewer-1. Review component implementations against VSM specs.
    VSM directory: tmp/arc/${id}/vsm/
    Output directory: tmp/arc/${id}/design-reviews/
    Fidelity threshold: ${fidelityThreshold}
    [inject agent review/design-implementation-reviewer.md content]
    [inject skill design-sync/references/fidelity-scoring.md content]

    GLYPH BUDGET PROTOCOL:
    Write ALL detailed findings to output files.
    Return ONLY: file path + 1-sentence summary (max 50 words).`
})

// ═══════════════════════════════════════════════════════
// STEP 4: MONITOR REVIEW
// ═══════════════════════════════════════════════════════

waitForCompletion(["design-reviewer-1"], { timeoutMs })

// ═══════════════════════════════════════════════════════
// STEP 5: AGGREGATE SCORES
// ═══════════════════════════════════════════════════════

const reviewFiles = Glob(`tmp/arc/${id}/design-reviews/*.md`)
let totalScore = 0
let componentCount = 0
const componentScores = {}
let p1Count = 0

for (const reviewFile of reviewFiles) {
  const content = Read(reviewFile)
  const componentName = reviewFile.replace(/.*\//, '').replace('.md', '')

  // Extract fidelity score from review output
  const scoreMatch = content.match(/\*?\*?Fidelity Score:\s*(\d+)\/100/)
  const score = scoreMatch ? parseInt(scoreMatch[1]) : 0

  // Count P1 findings by checking for FIDE- prefixed findings within P1 section
  const p1Section = content.split('### P1')[1]?.split('### P2')[0] ?? ''
  const p1Findings = p1Section.match(/\[FIDE-\d+\]/g) || []

  componentScores[componentName] = score
  totalScore += score
  componentCount++
  p1Count += p1Findings.length
}

const overallFidelity = componentCount > 0 ? Math.round(totalScore / componentCount) : 0
const verdict = p1Count > 0 ? "FAIL" : overallFidelity >= fidelityThreshold ? "PASS" : "NEEDS_WORK"

// ═══════════════════════════════════════════════════════
// STEP 6: WRITE VERIFICATION REPORT
// ═══════════════════════════════════════════════════════

const report = `# Design Verification Report

**Overall Fidelity: ${overallFidelity}/100** — ${verdict}
**Threshold: ${fidelityThreshold}**
**Components Reviewed: ${componentCount}**
**P1 Findings: ${p1Count}**

## Per-Component Scores

| Component | Score | Verdict |
|-----------|-------|---------|
${Object.entries(componentScores).map(([name, score]) =>
  `| ${name} | ${score}/100 | ${score >= fidelityThreshold ? 'PASS' : 'NEEDS_WORK'} |`
).join('\n')}

## Detail Reports

${reviewFiles.map(f => `- [${f.replace(/.*\//, '')}](${f})`).join('\n')}

<!-- SEAL: design-verification-complete -->
`

Write(`tmp/arc/${id}/design-verification.md`, report)

// ═══════════════════════════════════════════════════════
// STEP 7: CLEANUP
// ═══════════════════════════════════════════════════════

SendMessage({ type: "shutdown_request", recipient: "design-reviewer-1" })
sleep(15_000)

try {
  TeamDelete()
} catch (e) {
  const CHOME = process.env.CLAUDE_CONFIG_DIR || `${HOME}/.claude`
  Bash(`rm -rf "${CHOME}/teams/arc-design-verify-${id}" "${CHOME}/tasks/arc-design-verify-${id}" 2>/dev/null`)
}

updateCheckpoint({
  phase: "design_verification", status: "completed",
  artifact: `tmp/arc/${id}/design-verification.md`,
  artifact_hash: sha256(Read(`tmp/arc/${id}/design-verification.md`)),
  phase_sequence: 5.2,
  team_name: `arc-design-verify-${id}`,
  fidelity_score: overallFidelity,
  fidelity_verdict: verdict,
  component_scores: componentScores,
  p1_count: p1Count
})
```

## Checkpoint Integration

The `fidelity_score` in the checkpoint is consumed by Phase 7.6 DESIGN_ITERATION:

```javascript
// Phase 7.6 gate check:
if (checkpoint.phases.design_verification.fidelity_score < fidelityThreshold) {
  // Trigger design iteration loop
}
```

## Crash Recovery

| Resource | Location |
|----------|----------|
| Team config | `$CHOME/teams/arc-design-verify-{id}/` |
| Task list | `$CHOME/tasks/arc-design-verify-{id}/` |
| Review files | `tmp/arc/{id}/design-reviews/` |
| Verification report | `tmp/arc/{id}/design-verification.md` |

Recovery: `prePhaseCleanup()` handles team eviction. Review files persist for re-aggregation.
