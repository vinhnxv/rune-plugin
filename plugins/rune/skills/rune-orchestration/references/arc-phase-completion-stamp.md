# Post-Arc: Plan Completion Stamp — Full Algorithm

Appends a persistent completion record to the plan file after arc finishes. Updates the plan's Status field. Creates an audit trail of arc executions.

**Team**: None (orchestrator-only, runs after Phase 8)
**Tools**: Read, Write, Bash (git queries)
**Timeout**: 30 seconds (fast — single file read+write)

**Inputs**: checkpoint (object, from .claude/arc/{id}/checkpoint.json), branch name (from checkpoint or git)
**Outputs**: Updated plan file with Status field + appended Completion Record
**Preconditions**: Arc pipeline has finished (all phases completed, skipped, or failed). Plan file exists on disk.
**Error handling**: Plan file not found → warn + skip. Write fails → warn + skip (read-only file or permission error). No completed phases → skip stamp.

**Consumers**: arc.md (post-completion stub)

> **Note**: `sha256()`, `updateCheckpoint()`, `exists()`, and `warn()` are dispatcher-provided utilities available in the arc orchestrator context. Phase reference files call these without import.

## Algorithm

```javascript
// STEP 1: Validate plan path (defense-in-depth — arc init already validates)
const planPath = checkpoint.plan_file
if (!planPath || !/^[a-zA-Z0-9._\/-]+$/.test(planPath) || planPath.includes('..')) {
  warn(`Invalid plan path in checkpoint: ${planPath}`)
  return
}
if (!exists(planPath)) {
  warn("Plan file not found — skipping completion stamp")
  return
}

// STEP 2: Guard — skip if no phases completed
const hasAnyCompleted = Object.values(checkpoint.phases)
  .some(p => p.status === "completed")
if (!hasAnyCompleted) {
  warn("Arc has no completed phases — skipping completion stamp")
  return
}

// STEP 3: Determine overall status
const allCompleted = Object.values(checkpoint.phases)
  .every(p => p.status === "completed" || p.status === "skipped")
const anyFailed = Object.values(checkpoint.phases)
  .some(p => p.status === "failed" || p.status === "timeout")
const newStatus = allCompleted ? "Completed" : anyFailed ? "Failed" : "Partial"

// STEP 4: Read plan content
let content = Read(planPath)

// STEP 5: Update Status field (if present in first 50 lines)
// Limit search to first 50 lines to avoid false matches in previously appended records
const lines = content.split('\n')
const first50 = lines.slice(0, 50).join('\n')
if (first50.includes("**Status**:")) {
  // Find and replace only in the first 50 lines
  const statusLine = lines.findIndex((l, i) => i < 50 && l.includes("**Status**:"))
  if (statusLine !== -1) {
    lines[statusLine] = lines[statusLine].replace(/\*\*Status\*\*: \w+/, `**Status**: ${newStatus}`)
    content = lines.join('\n')
  }
}

// STEP 6: Build completion record
const record = buildCompletionRecord(checkpoint, newStatus)

// STEP 7: Append record (single atomic write)
content += "\n\n---\n\n" + record

// STEP 8: Write updated content
try {
  Write(planPath, content)
} catch (err) {
  warn(`Failed to write completion stamp to ${planPath}: ${err.message}`)
}
```

## buildCompletionRecord()

Pure function — no tool calls. Formats checkpoint data into a markdown completion record.

```javascript
function buildCompletionRecord(checkpoint, newStatus) {
  const completedAt = new Date().toISOString()
  const startedAt = checkpoint.started_at ? Date.parse(checkpoint.started_at) : Date.now()
  const duration = Math.round((Date.now() - startedAt) / 60000)

  // Use branch from checkpoint or fall back to current branch
  // Prefer checkpoint data over live git query (branch may have changed during arc)
  const branch = Bash("git branch --show-current 2>/dev/null").stdout.trim() || "unknown"

  // Count existing completion records for run ordinal
  const existingRecords = (Read(checkpoint.plan_file).match(/## Arc Completion Record/g) || []).length

  // Phase results table
  const phases = [
    ['1',   'FORGE',           'forge'],
    ['2',   'PLAN REVIEW',     'plan_review'],
    ['2.5', 'PLAN REFINEMENT', 'plan_refine'],
    ['2.7', 'VERIFICATION',    'verification'],
    ['5',   'WORK',            'work'],
    ['5.5', 'GAP ANALYSIS',    'gap_analysis'],
    ['6',   'CODE REVIEW',     'code_review'],
    ['7',   'MEND',            'mend'],
    ['7.5', 'VERIFY MEND',     'verify_mend'],
    ['8',   'AUDIT',           'audit'],
  ]

  let phaseTable = "| # | Phase | Status | Detail |\n|---|-------|--------|--------|\n"
  for (const [num, name, key] of phases) {
    const phase = checkpoint.phases[key]
    const tstat = phase?.status || "pending"
    const detail = phase?.artifact ? phase.artifact.split('/').pop() : "—"
    phaseTable += `| ${num} | ${name} | ${tstat} | ${detail} |\n`
  }

  // Convergence history
  let convergenceSection = ""
  const history = checkpoint.convergence?.history || []
  if (history.length > 0) {
    convergenceSection = `### Convergence\n\n- ${history.length + 1} mend pass(es)\n`
    for (const entry of history) {
      convergenceSection += `- Round ${entry.round}: ${entry.findings_before} → ${entry.findings_after} findings (${entry.verdict})\n`
    }
  } else {
    convergenceSection = `### Convergence\n\n- 1 mend pass (no retries needed)\n`
  }

  // Summary
  const commitCount = (checkpoint.commits || []).length
  const runOrdinal = existingRecords + 1

  return `## Arc Completion Record — Run ${runOrdinal}\n\n` +
    `**Completed at**: ${completedAt}\n` +
    `**Duration**: ${duration} min\n` +
    `**Arc ID**: ${checkpoint.id}\n` +
    `**Branch**: ${branch}\n` +
    `**Checkpoint**: .claude/arc/${checkpoint.id}/checkpoint.json\n\n` +
    `### Phase Results\n\n` +
    phaseTable + `\n` +
    convergenceSection + `\n` +
    `### Summary\n\n` +
    `- **Commits**: ${commitCount} on branch \`${branch}\`\n` +
    `- **Overall status**: ${newStatus}\n`
}
```

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| Plan file deleted during arc | Skip stamp, log warning (STEP 1) |
| Plan has no `**Status**:` field | Skip Status update, still append record (STEP 5) |
| Plan already has a Completion Record (re-run) | Append a NEW record with incremented run ordinal |
| Arc halted mid-pipeline (timeout/failure) | Still stamp with `Partial` or `Failed` status |
| All phases skipped (no completed phases) | Skip stamp entirely (STEP 2 guard) |
| Read-only file or write permission error | Warn + skip (STEP 8 try-catch) |
| Plan path tampered in checkpoint | Reject with warning (STEP 1 validation) |
