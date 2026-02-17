# Chunk Orchestrator — Chunked Review Pipeline

> Wraps the existing Roundtable Circle in a chunking loop when `changed_files.length > CHUNK_THRESHOLD`.
> The inner Roundtable Circle (7-phase lifecycle) remains a black box — chunking wraps, never modifies it.
> Lives in `review.md` Phase 0 (routing branch) and delegates detail to this reference.

## Chunk Decision Routing

This routing check lives in **review.md Phase 0** as a conditional branch — not a separate phase.

```javascript
// Phase 0: Pre-flight + chunk decision (routing concern, not a new pipeline phase)
const CHUNK_THRESHOLD   = config?.chunk_threshold   ?? 20
const CHUNK_TARGET_SIZE = config?.chunk_target_size ?? 15
const MAX_CHUNKS        = config?.max_chunks        ?? 5

const noChunk = flags.includes('--no-chunk')

if (changed_files.length <= CHUNK_THRESHOLD || noChunk) {
  // ── SINGLE-PASS ──────────────────────────────────────────────────────────
  // Zero behavioral change — existing Roundtable Circle, unmodified
  runSinglePassReview(changed_files, identifier, flags)
} else {
  // ── CHUNKED REVIEW ───────────────────────────────────────────────────────
  // See: chunk-orchestrator.md for full lifecycle
  runChunkedReview(changed_files, identifier, flags, config)
}
```

## `--dry-run` Output Format

When `--no-chunk` is absent and `--dry-run` is present, print the chunk plan and exit without reviewing:

```
Chunked Review Plan — dry run
══════════════════════════════════════════════════════════

Files: 34  |  Chunks: 3  |  Tier: STANDARD (max 2 re-reviews)
Token cost: ~3x single-pass review (one Roundtable Circle per chunk)

Chunk 1 — plugins/rune/commands/ (12 files, complexity: 18.4)
  plugins/rune/commands/review.md         [md,  complexity: 0.5]
  plugins/rune/commands/arc.md            [md,  complexity: 0.5]
  plugins/rune/commands/work.md           [md,  complexity: 0.5]
  ... (9 more)

Chunk 2 — plugins/rune/skills/ (14 files, complexity: 21.7)
  plugins/rune/skills/roundtable-circle/SKILL.md  [md, complexity: 0.5]
  ... (13 more)

Chunk 3 — plugins/rune/agents/ (8 files, complexity: 9.2)
  ... (8 files)

Security pins (read-only context in every chunk):
  plugins/rune/scripts/enforce-readonly.sh
  plugins/rune/hooks/hooks.json

Run without --dry-run to begin review.
```

## Token Cost Warning

Before the first TeamCreate, always display the cost multiplier:

```javascript
const chunkCount = Math.min(chunks.length, MAX_CHUNKS)
log(`\nToken cost notice: Chunked review runs ${chunkCount} Roundtable Circle passes.`)
log(`Estimated cost: ~${chunkCount}x a single-pass review of comparable file count.`)
log(`Convergence tier: ${tier.name} — up to ${tier.maxRounds + 1} total passes if re-reviews triggered.`)
log(`Use --no-chunk to force single-pass, or --no-converge to disable re-review rounds.\n`)
```

## Per-Chunk Roundtable Circle Lifecycle

Each chunk runs a full team lifecycle: create → review → cleanup.
The inner Roundtable Circle is invoked unchanged — chunk parameters are passed as context only.

```javascript
async function runChunkReview(chunk, identifier, flags, securityPins, arcRemainingMs) {
  const teamName  = `rune-review-${identifier}-chunk-${chunk.chunkIndex}`  // disambiguated
  const chunkDir  = `tmp/reviews/${identifier}/chunk-${chunk.chunkIndex}`
  const tomePath  = `${chunkDir}/TOME.md`

  mkdir(chunkDir)

  // Dynamic per-chunk timeout — scales with remaining arc budget
  // Floor at 3 min to prevent zero-timeout edge cases
  const perChunkTimeout = arcRemainingMs
    ? Math.max(Math.floor(arcRemainingMs / chunkCount), 180_000)
    : 660_000  // 11 min default when not in arc context

  // ── PRE-CREATE GUARD ──────────────────────────────────────────────────────
  // See: team-lifecycle-guard.md for the canonical 3-step escalation pattern
  // Step 1: try TeamDelete (graceful)
  // Step 2: rm -rf target team dirs (filesystem fallback)
  // Step 3: cross-workflow find scan + retry TeamDelete
  applyPreCreateGuard(teamName)

  // ── TEAM CREATE ───────────────────────────────────────────────────────────
  TeamCreate({ team_name: teamName })

  // ── ROUNDTABLE CIRCLE (inner black box) ───────────────────────────────────
  // Pass chunk.files as the review scope.
  // securityPins are contextFiles: read-only references, not budgeted files.
  Task({
    team_name: teamName,
    subagent_type: 'general-purpose',
    prompt: buildRoundtablePrompt({
      files:        chunk.files.map(f => f.file ?? f),
      contextFiles: securityPins,  // Read-only security pins for every chunk
      identifier:   teamName,
      outputDir:    chunkDir,
      flags,
    }),
  })

  // ── MONITOR ───────────────────────────────────────────────────────────────
  waitForCompletion(teamName, perChunkTimeout)  // see monitor-utility.md

  // ── COLLECT OUTPUT ────────────────────────────────────────────────────────
  const tomeMd = Read(tomePath) ?? buildPartialTome(chunkDir, chunk)
  // If full TOME not written (timeout), collect completed Ash outputs:
  //   glob: tmp/reviews/{id}/chunk-{N}/ash-*-runes.md
  //   status: 'completed_partial', Coverage Gaps for timed-out Ashes

  // ── PRE-DELETE GUARD + CLEANUP ────────────────────────────────────────────
  // Broadcast shutdown, wait for teammate acknowledgements, then TeamDelete
  // rm -rf fallback if TeamDelete fails (see team-lifecycle-guard.md)
  shutdownAndCleanup(teamName)

  writeChunkProgress(identifier, chunk.chunkIndex, 'completed')
  return { chunkIndex: chunk.chunkIndex, tome: tomeMd, path: tomePath }
}
```

## Full Chunked Review Orchestration

```javascript
async function runChunkedReview(changed_files, identifier, flags, config) {
  // ── SCORING + GROUPING ────────────────────────────────────────────────────
  const diffStats    = parseDiffNumstat()  // git diff --numstat: batch call, not per-file
  const scoredFiles  = changed_files.map(f => scoreFile(f, diffStats))
  const chunks       = groupIntoChunks(scoredFiles, CHUNK_TARGET_SIZE)
  const chunkCount   = Math.min(chunks.length, MAX_CHUNKS)
  const securityPins = collectSecurityPins(scoredFiles)

  // ── CONVERGENCE TIER ─────────────────────────────────────────────────────
  const convergenceEnabled = !flags.includes('--no-converge') &&
                             (config?.convergence_enabled ?? true)
  const tier = selectConvergenceTier(scoredFiles, chunks, config)

  // ── TOKEN COST WARNING ────────────────────────────────────────────────────
  displayCostWarning(chunkCount, tier)

  // ── DRY RUN ───────────────────────────────────────────────────────────────
  if (flags.includes('--dry-run')) {
    displayDryRunPlan(chunks, tier, securityPins, chunkCount)
    return
  }

  // ── CONVERGENCE STATE ─────────────────────────────────────────────────────
  const convergenceHistory = []  // [{ round, chunk_metrics, verdict, timestamp }]
  let chunksToReview = chunks.slice(0, chunkCount)
  let allChunkTomes  = []  // Full set: updated on re-reviews, preserved otherwise
  let unifiedTome    = null

  // ── CONVERGENCE OUTER LOOP ────────────────────────────────────────────────
  for (let round = 0; round <= (convergenceEnabled ? tier.maxRounds : 0); round++) {
    const isReReview = round > 0
    log(`\n=== ${isReReview ? `Re-review round ${round}` : 'Initial review'} — ${chunksToReview.length} chunks ===`)

    // ── PER-CHUNK INNER LOOP ────────────────────────────────────────────────
    const roundTomes = []
    for (const chunk of chunksToReview) {
      const roundLabel = isReReview ? `-r${round}` : ''
      log(`\n--- Chunk ${chunk.chunkIndex + 1}/${chunkCount}${roundLabel}: ${chunk.files.length} files ---`)

      // On re-review: inject cross-chunk context to improve low-quality chunks
      const contextFiles = isReReview
        ? selectCrossChunkContext(chunk, chunks, unifiedTome)
        : []

      // Apply pre-create guard BEFORE every TeamCreate (between chunks too)
      const result = await runChunkReview(chunk, identifier, flags, [
        ...securityPins,
        ...contextFiles,
      ])
      roundTomes.push(result)
    }

    // ── CROSS-CHUNK TOME MERGE ────────────────────────────────────────────
    // On re-review: replace only re-reviewed chunk TOMEs; keep others from prior round
    if (isReReview) {
      allChunkTomes = replaceChunkTomes(allChunkTomes, roundTomes, chunksToReview)
    } else {
      allChunkTomes = roundTomes
    }

    unifiedTome = mergeChunkTomes(allChunkTomes, identifier)
    Write(`tmp/reviews/${identifier}/TOME.md`, unifiedTome)

    // ── CONVERGENCE GATE ──────────────────────────────────────────────────
    if (!convergenceEnabled) {
      convergenceHistory.push({ round, chunk_metrics: null, verdict: 'disabled', timestamp: now() })
      break
    }

    const { verdict, flaggedChunks, chunkMetrics } = evaluateConvergence(
      unifiedTome, chunksToReview, chunks, round, convergenceHistory
    )
    convergenceHistory.push({ round, chunk_metrics: chunkMetrics, verdict, timestamp: now() })

    if (verdict === 'converged') {
      log(`✓ Convergence achieved at round ${round}`)
      break
    } else if (verdict === 'halted') {
      warn(`⚠ Convergence halted: ${chunkMetrics.reason ?? 'metrics not improving'}. Proceeding with current TOME.`)
      break
    } else if (verdict === 'retry') {
      log(`↻ Re-review needed: ${flaggedChunks.length} chunk(s) below quality threshold`)
      chunksToReview = flaggedChunks
    }
  }

  // ── OPTIONAL CROSS-CUTTING PASS ───────────────────────────────────────────
  if (shouldRunCrossCuttingPass(unifiedTome, chunks, config)) {
    runCrossCuttingPass(identifier, chunks, unifiedTome)
  }

  // ── CONVERGENCE REPORT ────────────────────────────────────────────────────
  const report = generateConvergenceReport(convergenceHistory, chunks, identifier, tier)
  Write(`tmp/reviews/${identifier}/convergence-report.md`, report)

  log(`\nChunked review complete. Unified TOME: tmp/reviews/${identifier}/TOME.md`)
  log(`Convergence report:      tmp/reviews/${identifier}/convergence-report.md`)
}
```

## Cross-Chunk TOME Merge

Finding IDs use **standard `{PREFIX}-{NUM}` format**. Chunk attribution is via `chunk="N"` attribute
in `<!-- RUNE:FINDING -->` HTML comment — NOT a `C{N}-PREFIX-NUM` prefix. This preserves dedup and
parsing compatibility with existing tooling.

```javascript
function mergeChunkTomes(chunkResults, identifier) {
  const allFindings = []

  for (const { chunkIndex, tome } of chunkResults) {
    const findings = parseRuneFindings(tome)
    for (const finding of findings) {
      // Standard ID preserved — chunk attributed via HTML comment attribute
      // e.g., <!-- RUNE:FINDING id="BACK-001" chunk="1" severity="P1" -->
      finding.chunk = chunkIndex + 1
      allFindings.push(finding)
    }
  }

  // Cross-chunk dedup: key on (file, line_range_bucket, category)
  // Category prevents false merge of SEC vs QUAL findings in 5-line window
  // Strip no prefix — IDs are standard, dedup keys on content not ID
  const deduped = dedupFindings(allFindings, {
    windowLines: 5,
    keyFn: f => `${f.file}:${lineBucket(f.line, 5)}:${f.category}`,
  })

  const chunkSummary = chunkResults.map(({ chunkIndex, tome }) => ({
    chunk: chunkIndex + 1,
    findings: parseFindingCount(tome),
    files:    parseFileCount(tome),
  }))

  return formatTome(deduped, {
    header: [
      `# TOME — Review Summary (Chunked: ${chunkResults.length} chunks)`,
      ``,
      `**Chunks:** ${chunkResults.length}`,
      `**Total findings:** ${deduped.length} (from ${allFindings.length} pre-dedup)`,
    ].join('\n'),
    chunkSummary,
  })
}

function replaceChunkTomes(existing, updated, updatedChunks) {
  const updatedIndices = new Set(updatedChunks.map(c => c.chunkIndex))
  const updatedByIndex = Object.fromEntries(updated.map(r => [r.chunkIndex, r]))
  return existing.map(r =>
    updatedIndices.has(r.chunkIndex) ? updatedByIndex[r.chunkIndex] : r
  )
}
```

## Chunk Progress Tracking

Chunk state is written to `tmp/reviews/{id}/chunk-{N}/.status` for `--resume` support.

```javascript
// Chunk state machine: pending → in_progress → completed | completed_partial | failed
function writeChunkProgress(identifier, chunkIndex, status) {
  // 'completed_partial' when chunk timed out but partial Ash outputs were collected
  Write(`tmp/reviews/${identifier}/chunk-${chunkIndex}/.status`, JSON.stringify({
    chunkIndex, status, timestamp: now(),
  }))
}

// On --resume: read .status markers to skip completed chunks
function getCompletedChunks(identifier, chunkCount) {
  return Array.from({ length: chunkCount }, (_, i) => i).filter(i => {
    try {
      const s = JSON.parse(Read(`tmp/reviews/${identifier}/chunk-${i}/.status`) ?? '{}')
      return s.status === 'completed'  // Skip completed only; retry completed_partial and failed
    } catch (_) { return false }
  })
}
```

## Cross-Cutting Pass (Optional)

Only runs when 3+ chunks span 3+ distinct top-level directories. Uses a single Explore agent (haiku,
read-only, 3-minute timeout). Skipped on timeout — does not block the review.

```javascript
function shouldRunCrossCuttingPass(unifiedTome, chunks, config) {
  if (config?.cross_cutting_pass === false) return false
  if (chunks.length < 3) return false
  const topDirs = new Set(chunks.flatMap(c =>
    c.files.map(f => (f.file ?? f).split('/')[0])
  ))
  return topDirs.size >= 3
}
```

## Arc Integration — Dynamic Timeout

When invoked from arc Phase 6, chunk count and convergence tier constrain timeout:

```javascript
// arc.md Phase 6 — compute adjusted timeout before delegating to review.md
const maxChunksForBudget = Math.floor(arcRemainingMs / PHASE_TIMEOUTS.code_review)
const chunkCount         = Math.min(chunks.length, MAX_CHUNKS, maxChunksForBudget)
const perChunkTimeout    = Math.max(Math.floor(arcRemainingMs / chunkCount), 180_000)

// Arc checkpoint v5: add chunks tracking to code_review phase
updateCheckpoint({
  phase: 'code_review', status: 'in_progress', schema_version: 5,
  chunks: { total: chunkCount, completed: 0, tomes: [] },
})
```

## References

- [Chunk Scoring](chunk-scoring.md) — `scoreFile`, `groupIntoChunks`, security pins
- [Convergence Gate](convergence-gate.md) — Tier selection, quality metrics, decision matrix
- [Dedup Runes](dedup-runes.md) — Cross-chunk dedup algorithm and finding ID format
- [Team Lifecycle Guard](../../rune-orchestration/references/team-lifecycle-guard.md) — Pre-create guard (3-step escalation)
- [Monitor Utility](monitor-utility.md) — `waitForCompletion` parameters per command
- [Smart Selection](smart-selection.md) — Ash budgets and file classification
