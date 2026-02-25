---
name: roundtable-circle
description: |
  Use when running /rune:appraise or /rune:audit, when spawning multiple review
  agents, when TOME aggregation fails or produces malformed output, or when a
  TeammateIdle hook fires before expected output is written. Handles 7-phase
  lifecycle (pre-flight, Rune Gaze, inscription, spawn, monitor, aggregate,
  cleanup) for up to 8 parallel reviewers. Use when team cleanup fails after
  a review, when on-teammate-idle.sh blocks review completion, or when
  roundtable phases need to be re-entered after session resume.
  Keywords: roundtable, appraise, audit, TOME aggregation, inscription, Ash,
  team lifecycle, TeammateIdle, 7-phase, 8 reviewers, SEAL marker.

  <example>
  Context: Running a code review
  user: "/rune:appraise"
  assistant: "Loading roundtable-circle for Agent Teams review orchestration"
  </example>
user-invocable: false
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

# Roundtable Circle Skill

Orchestrates multi-agent code reviews using Claude Code Agent Teams. Each Ash teammate gets its own dedicated context window, eliminating single-context bottlenecks.

## Iron Law

> **NO REVIEW WITHOUT INSCRIPTION** (INS-001)
>
> This rule is absolute. No exceptions for "simple" changes, time pressure,
> or pragmatism arguments. If you find yourself rationalizing an exception,
> you are about to violate this law.

## Architecture

### 7-Phase Lifecycle

```
Phase 0:   Pre-flight     → Validate git status, check for changes
Phase 1:   Rune Gaze      → git diff → classify files → select Ash
Phase 2:   Forge Team      → TeamCreate + TaskCreate + inscription.json
Phase 3:   Summon           → Fan-out Ash with self-organizing prompts
Phase 4:   Monitor         → TaskList polling, 5-min stale detection
Phase 4.5: Doubt Seer     → Cross-examine Ash findings (conditional)
Phase 5:   Aggregate       → Summon Runebinder → writes TOME.md
Phase 6:   Verify          → Truthsight validation on P1 findings
Phase 6.2: Diff Verify     → Codex cross-model P1/P2 verification (v1.51.0+)
Phase 6.3: Arch Review     → Codex architecture review (audit mode only, v1.51.0+)
Phase 7:   Cleanup         → Shutdown requests → approvals → TeamDelete
```

### Built-in Ash Roles (Max 7)

| Ash | Role | When Selected | Perspectives |
|-----------|------|---------------|-------------|
| **Forge Warden** | Backend review | Backend files changed | Architecture, performance, logic bugs, duplication |
| **Ward Sentinel** | Security review | Every review | Vulnerabilities, auth, injection, OWASP |
| **Pattern Weaver** | Quality patterns | Every review | Simplicity, TDD, dead code, pattern consistency |
| **Veil Piercer** | Truth-telling review | Every review | Premise validation, production viability, long-term consequences |
| **Glyph Scribe** | Frontend review | Frontend files changed | TypeScript safety, React performance, accessibility |
| **Knowledge Keeper** | Docs review | Docs changed (>= 10 lines) | Accuracy, completeness, anti-injection |
| **Codex Oracle** | Cross-model review | `codex` CLI available | Cross-model security, logic, quality (GPT-5.3-codex) |

Plus **Runebinder** (utility) for aggregation in Phase 5.

### Custom Ashes (Extensible)

Projects can register additional Ash from local agents, global agents, or other plugins via `talisman.yml`. Custom Ashes join the standard lifecycle:

- **Wrapped** with Truthbinding Protocol (evidence, Glyph Budget, Seal format)
- **Summoned** alongside built-ins in Phase 3 (parallel execution)
- **Deduplicated** using their unique `finding_prefix` in the extended hierarchy
- **Verified** by Truthsight (if `settings.verification.layer_2_custom_agents: true`)
- **Aggregated** into TOME.md by Runebinder

**Max total:** 7 built-in + up to 2 custom = 9 Ashes (configurable via `settings.max_ashes`). The cap exists because each Ash output (~10k tokens) consumes verifier context budget. Custom Ash ceiling: 2 (total max: 9 = 7 built-in + 2 custom). Increased from 5+3 in v1.17.0 to 6+2 in v1.18.0, then to 7+2 in v1.43.0 (Veil Piercer).

**Migration note (v1.18.0):** Custom Ash ceiling reduced from 3 to 2 due to Codex Oracle addition. Projects using 3 custom Ashes should reduce to 2 or disable Codex Oracle via `talisman.codex.disabled: true`.

See [`custom-ashes.md`](references/custom-ashes.md) for full schema, wrapper prompt template, and examples.

### Output Directory Structure

```
tmp/reviews/{id}/
├── inscription.json         # Output contract (generated Phase 2)
├── forge-warden.md          # Backend review findings
├── ward-sentinel.md         # Security review findings
├── pattern-weaver.md        # Quality patterns findings
├── veil-piercer.md          # Truth-telling findings
├── glyph-scribe.md          # Frontend review findings (if summoned)
├── knowledge-keeper.md      # Docs review findings (if summoned)
├── codex-oracle.md          # Cross-model review findings (if codex CLI available)
├── TOME.md                  # Aggregated + deduplicated findings
├── truthsight-report.md     # Verification results (if Layer 2 enabled)
├── codex-diff-verification.md  # Codex diff verification (Phase 6.2, v1.51.0+)
└── architecture-review.md   # Codex architecture review (Phase 6.3, audit only, v1.51.0+)
```

### Audit Mode

`/rune:audit` reuses the same 7-phase lifecycle with one difference in Phase 0:

| Aspect | Review (`/rune:appraise`) | Audit (`/rune:audit`) |
|--------|------------------------|----------------------|
| Phase 0 input | `git diff` (changed files) | `find` (all project files) |
| Identifier | PR number / branch name | Timestamp (`YYYYMMDD-HHMMSS`) |
| Output directory | `tmp/reviews/{id}/` | `tmp/audit/{id}/` |
| State file | `tmp/.rune-review-{id}.json` | `tmp/.rune-audit-{id}.json` |
| Team name | `rune-review-{id}` | `rune-audit-{id}` |
| Git required | Yes | No |
| File prioritization | New/modified files first | Entry points/core modules first |

Phases 1-7 are identical. Same Ash, same inscription schema, same dedup, same verification. Audit file prioritization differs: importance-based (entry points, core modules) instead of recency-based (new files, modified files).

### Audit-Specific: Truthseer Validator

For audits with high file counts (>100 reviewable files), a **Truthseer Validator** phase runs between Phase 5 and Phase 6:

```
Phase 5.5: Truthseer Validator
  1. Read all Ash outputs
  2. Cross-reference finding density against file importance
  3. Flag under-reviewed areas (high-importance files with 0 findings)
  4. Score confidence per Ash based on evidence quality
  5. Write validation summary to {output_dir}/validator-summary.md
```

The Validator ensures audit coverage quality by detecting:
- **Under-coverage**: Critical files reviewed but no findings (suspicious silence)
- **Over-confidence**: High finding counts with low evidence quality
- **Scope gaps**: Files in budget that weren't actually read

See [Validator Rules](references/validator-rules.md) for confidence scoring and risk classification.

## Phase 0: Pre-flight

```bash
# Unified scope (see /rune:appraise command for full implementation):
# committed: git diff --name-only --diff-filter=ACMR "${default_branch}...HEAD"
# staged: git diff --cached --name-only --diff-filter=ACMR
# unstaged: git diff --name-only
# untracked: git ls-files --others --exclude-standard
# Merged, deduplicated, filtered for existence and non-symlinks
```

**Abort conditions:**
- No files changed → "Nothing to review"
- Only non-reviewable files (images, lock files) → "No reviewable changes"

**Docs-only override:** If all non-skip files are doc-extension and all fall below the line threshold (no code files), promote them so Knowledge Keeper is still summoned. See `rune-gaze.md` for algorithm.

## Phase 1: Rune Gaze (Scope Selection)

Classify changed files by extension to determine which Ash to summon.

See [Rune Gaze](references/rune-gaze.md) for the full file classification algorithm.

**Quick reference:**

| File Pattern | Ash |
|-------------|-----------|
| `*.py, *.go, *.rs, *.rb, *.java` | Forge Warden |
| `*.ts, *.tsx, *.js, *.jsx` | Glyph Scribe |
| `Dockerfile, *.sh, *.sql, *.tf, CI/CD` | Forge Warden (infra) |
| `*.yml, *.yaml, *.json, *.toml, *.ini` | Forge Warden (config) |
| `*.md` (>= 10 lines changed) | Knowledge Keeper |
| `.claude/**/*.md` | Knowledge Keeper + Ward Sentinel |
| Unclassified (not skip, not any group) | Forge Warden (catch-all) |
| ALL files | Ward Sentinel (always) |
| ALL files | Pattern Weaver (always) |
| ALL files | Veil Piercer (always) |

### Large-Diff Detection (Post-Phase 1)

After file classification, check total file count against the large-diff threshold:

```javascript
const LARGE_DIFF_THRESHOLD = talisman?.review?.large_diff_threshold ?? 25
const CHUNK_SIZE = talisman?.review?.chunk_size ?? 15

if (totalFiles > LARGE_DIFF_THRESHOLD && depth !== "deep") {
  // Standard depth only — deep mode uses wave-based chunking already
  inscription.chunked = true
  inscription.chunk_size = CHUNK_SIZE
  inscription.chunks = splitIntoChunks(changedFiles, CHUNK_SIZE)
  log(`Large diff detected (${totalFiles} files). Chunked review: ${inscription.chunks.length} chunks of up to ${CHUNK_SIZE} files.`)
}
```

`splitIntoChunks(files, size)` partitions the files array into sequential slices, preserving classification order (high-priority files first). Each chunk is a sub-array passed as the file list to that chunk's Ash wave.

**Conditions:**
- Only activates when `totalFiles > LARGE_DIFF_THRESHOLD` (default: 25)
- Skipped in `depth=deep` mode (wave system handles chunking natively)
- Skipped in `scope=full` audit mode (audit uses importance-based priority, not diff-scoped chunking)
- Talisman overrides: `review.large_diff_threshold` and `review.chunk_size`

### Inscription Sharding Decision (Post-Phase 1, v1.98.0+)

After existing large-diff detection, run the shard decision for standard depth + diff scope.
See [shard-allocator.md](references/shard-allocator.md) for the full algorithm.

```javascript
// === Inscription Sharding Decision (Post-Phase 1) ===
// Runs AFTER large-diff detection above. Sharding replaces chunking for standard depth.
const SHARD_THRESHOLD  = talisman?.review?.shard_threshold    ?? 15
const SHARD_SIZE       = talisman?.review?.shard_size         ?? 12
const MAX_SHARDS       = Math.min(talisman?.review?.max_shards ?? 5, 26)  // Clamp to 26 (A-Z shard IDs)
const CROSS_SHARD      = talisman?.review?.cross_shard_sentinel ?? true
const MODEL_POLICY     = talisman?.review?.shard_model_policy  ?? "auto"

let shards = null
if (depth !== "deep" && scope === "diff" && totalFiles > SHARD_THRESHOLD) {
  // Sharding only for standard depth + diff scope
  // Deep mode uses wave-based specialists — sharding generalists over them is counterproductive
  shards = allocateShards(classifiedFiles, { SHARD_SIZE, MAX_SHARDS, MODEL_POLICY })

  if (shards) {
    inscription.sharding = {
      enabled: true,
      strategy: "domain-affinity",
      shard_count: shards.length,
      shard_threshold: SHARD_THRESHOLD,
      shard_size: SHARD_SIZE,
      shards: shards.map((s, i) => ({
        shard_id: String.fromCharCode(65 + i),           // A, B, C, D, E
        files: s.files.map(f => f.path),
        file_count: s.files.length,
        primary_domain: s.primary_domain,
        domains: [...s.domains],
        model: s.model,
        reviewer_name: `shard-reviewer-${String.fromCharCode(97 + i)}`,   // a, b, c, d, e
        output_file:   `shard-${String.fromCharCode(97 + i)}-findings.md`,
        summary_file:  `shard-${String.fromCharCode(97 + i)}-summary.json`
      })),
      cross_shard: CROSS_SHARD ? {
        enabled: true,
        reviewer_name: "cross-shard-sentinel",
        output_file: "cross-shard-findings.md",
        input_files: shards.map((_, i) => `shard-${String.fromCharCode(97 + i)}-summary.json`)
      } : { enabled: false }
    }

    // Sharding supersedes chunking for standard depth
    inscription.chunked = false

    log(
      `Inscription Sharding: ${shards.length} shards ` +
      `(${shards.map(s => s.files.length).join('+')} files). ` +
      `Cross-shard: ${CROSS_SHARD ? 'enabled' : 'disabled'}`
    )
  }
} else if (depth === "deep") {
  // Deep mode: waves handle file distribution. Sharding NOT used.
  inscription.sharding = { enabled: false }
}
```

**Decision matrix:**
```
depth=deep              → waves (existing) — sharding disabled
depth=standard, scope=diff, totalFiles > SHARD_THRESHOLD → SHARDING (new, v1.98.0+)
depth=standard, scope=diff, totalFiles <= SHARD_THRESHOLD → standard single-pass (unchanged)
depth=standard, scope=full → chunked review or single-pass (unchanged — audit mode)
```

**Escape hatch:** Set `shard_threshold: 999` in talisman.yml to disable sharding for all diffs.

## Phase 2: Forge Team

```
1. mkdir -p tmp/reviews/{pr-number}/
2. Generate inscription.json + signal directory (see references/monitor-utility.md)
3. After signal directory setup, write SEC-001 readonly marker:
   Write(`tmp/.rune-signals/{team_name}/.readonly-active`, "active")
   (This enables platform-level read-only enforcement for review/audit Ashes via PreToolUse hook)
4. TeamCreate({ team_name: "rune-review-{pr}" })
5. For each selected Ash:
   TaskCreate({
     subject: "Review {scope} as {role}",
     description: "Files: [...], Output: tmp/reviews/{pr}/{role}.md"
   })
```

## Phase 3: Summon Ash

For each selected Ash in the current wave, summon as a background teammate:

```
Task({
  team_name: "rune-review-{pr}",
  name: "{ash-slug}",     // uses ash.slug — no wave suffix (preserves hook compatibility)
  subagent_type: "general-purpose",
  prompt: [from references/ash-prompts/{role}.md],
  run_in_background: true
})
```

Each Ash prompt includes:
- Truthbinding Protocol (ANCHOR + RE-ANCHOR)
- Task claiming via TaskList/TaskUpdate
- Glyph Budget enforcement
- Seal Format for completion

### Sharded Review Path (v1.98.0+, standard depth + large diff)

When `inscription.sharding?.enabled === true`, Phase 3 spawns shard reviewers in parallel
then a single Cross-Shard Sentinel after all shards complete.
See [shard-allocator.md](references/shard-allocator.md) for allocator algorithm and
[shard-reviewer.md](references/ash-prompts/shard-reviewer.md) for reviewer prompt template.

```javascript
if (inscription.sharding?.enabled) {
  // ─── SHARDED REVIEW PATH ───────────────────────────────────────────────────
  const { shards, cross_shard } = inscription.sharding

  // Step 1: Register shard reviewers in teammates[] for TeammateIdle hook
  for (const shard of shards) {
    inscription.teammates.push({
      name: shard.reviewer_name,
      output_file: shard.output_file,
      required_sections: ["P1 (Critical)", "P2 (High)", "P3 (Medium)", "Self-Review Log"]
    })
  }

  // Step 2: Spawn shard reviewers in PARALLEL
  for (const shard of shards) {
    const prompt = buildShardReviewerPrompt(shard, {
      outputDir,
      diffScope: inscription.diff_scope,
      innerFlame: true,
      seal: true
    })
    Task({
      team_name: teamName,
      name: shard.reviewer_name,
      subagent_type: "general-purpose",
      model: shard.model,
      prompt,
      run_in_background: true
    })
  }

  // Step 3: Monitor shard reviewers
  waitForCompletion(teamName, shards.length, {
    timeoutMs: 600_000,
    staleWarnMs: 300_000,
    pollIntervalMs: 30_000,
    label: `Shard review (${shards.length} shards)`
  })

  // Step 3.5: Validate shard outputs — handle timeout/crash gracefully
  const availableSummaries = []
  for (const shard of shards) {
    const summaryPath = `${outputDir}${shard.summary_file}`
    const findingsPath = `${outputDir}${shard.output_file}`
    if (fileExists(summaryPath)) {
      availableSummaries.push(summaryPath)
    } else if (fileExists(findingsPath)) {
      // Findings exist but summary missing — reviewer crashed mid-output
      // Generate minimal stub summary for Cross-Shard Sentinel
      log(`WARN: Shard ${shard.shard_id} missing summary JSON — generating stub`)
      Write(summaryPath, JSON.stringify({
        shard_id: shard.shard_id,
        files_reviewed: 0,
        finding_count: 0,
        finding_ids: [],
        file_summaries: [],
        cross_shard_signals: [],
        stub: true,
        stub_reason: "crash"
      }))
      availableSummaries.push(summaryPath)
    } else {
      // Both missing — shard reviewer fully timed out
      log(`WARN: Shard ${shard.shard_id} produced no output (timeout/crash)`)
      // Write stub so Cross-Shard Sentinel treats as coverage blind spot
      Write(summaryPath, JSON.stringify({
        shard_id: shard.shard_id,
        files_reviewed: 0,
        finding_count: 0,
        finding_ids: [],
        file_summaries: [],
        cross_shard_signals: [],
        stub: true,
        stub_reason: "timeout"
      }))
      availableSummaries.push(summaryPath)
    }
  }

  // Step 4: Spawn Cross-Shard Sentinel (SEQUENTIAL, after all shards done)
  // Note: subagent_type is "general-purpose" per ATE-1 (Agent Teams Enforcement).
  // The cross-shard-sentinel.md agent definition (tools: Read, Write) serves as
  // the prompt template, NOT as a platform-enforced tool restriction. The metadata-only
  // constraint is enforced via prompt ("MUST NOT read source files") — not platform-level.
  // This is an accepted design tradeoff: ATE-1 requires general-purpose for all teammates.
  if (cross_shard?.enabled && availableSummaries.length > 0) {
    // Reset .expected count: shards.length → 1 (for sentinel monitoring)
    Write(`${signalDir}/.expected`, "1")

    Task({
      team_name: teamName,
      name: cross_shard.reviewer_name,
      subagent_type: "general-purpose",
      model: resolveModelForAgent("cross-shard-sentinel", talisman),  // Cost tier mapping (references/cost-tier-mapping.md)
      prompt: buildCrossShardPrompt(availableSummaries, { outputDir }),
      run_in_background: true
    })

    waitForCompletion(teamName, 1, {
      timeoutMs: 180_000,
      staleWarnMs: 90_000,
      pollIntervalMs: 30_000,
      label: "Cross-shard analysis"
    })
  }

} else {
  // ─── NON-SHARDED PATH (chunked or standard single-pass — unchanged) ─────────
```

**Prompt builder contracts** (defined alongside `buildShardReviewerPrompt` in Phase 3 implementation):

```javascript
// buildCrossShardPrompt: generates the Cross-Shard Sentinel spawn prompt
function buildCrossShardPrompt(summaryFiles, opts) {
  // summaryFiles: array of absolute paths to shard-*-summary.json files
  // opts: { outputDir }
  // Returns: string — complete spawn prompt for the cross-shard sentinel
  const fileList = summaryFiles.map((f, i) => `${i + 1}. ${f}`).join('\n')
  return CROSS_SHARD_SENTINEL_TEMPLATE
    .replace('{summary_file_list}', fileList)
    .replace('{output_dir}', opts.outputDir)
}
```

**Phase 5 aggregation note:** Runebinder already reads all `*.md` files in `outputDir`.
Shard findings (`shard-a-findings.md`, etc.) and cross-shard findings (`cross-shard-findings.md`)
are standard finding files — Runebinder reads them without modification.
Shard summary JSONs (`shard-*-summary.json`) are skipped (JSON, not MD).
Finding prefixes `SH{X}-` and `XSH-` follow the 2-5 char convention — no Runebinder changes.

### Chunked Review Loop (standard depth, large diffs only)

When `inscription.chunked === true` (standard depth + large diff), Phase 3 processes chunks sequentially. Each chunk gets its own Ash wave over the same team:

```javascript
// Chunked review — standard depth large-diff path
if (inscription.chunked) {
  const chunks = inscription.chunks  // set in Phase 1 large-diff detection

  for (let chunkIdx = 0; chunkIdx < chunks.length; chunkIdx++) {
    const chunkFiles = chunks[chunkIdx]
    log(`Chunk ${chunkIdx + 1}/${chunks.length}: ${chunkFiles.length} files`)

    // Spawn Ashes for this chunk — same roles, scoped file list
    for (const ash of selectedAsh) {
      Task({
        team_name: teamName,
        name: ash.slug,   // no chunk suffix — preserves hook compatibility
        subagent_type: "general-purpose",
        prompt: buildAshPrompt(ash, {
          files: chunkFiles,
          chunkContext: `Chunk ${chunkIdx + 1} of ${chunks.length}. Prior chunk findings are at ${outputDir}TOME-chunk-${chunkIdx}.md (if exists).`
        }),
        run_in_background: true
      })
    }

    // Monitor this chunk's wave
    const result = waitForCompletion(teamName, selectedAsh.length, {
      timeoutMs: 600_000,
      staleWarnMs: 300_000,
      pollIntervalMs: 30_000,
      label: `Review chunk ${chunkIdx + 1}/${chunks.length}`
    })

    // Write interim TOME for this chunk (Runebinder reads all at Phase 5)
    Write(`${outputDir}TOME-chunk-${chunkIdx + 1}.md`,
      `# Chunk ${chunkIdx + 1}/${chunks.length} Findings\n\nFiles: ${chunkFiles.join(", ")}\n\n` +
      `(Partial — merged into final TOME.md by Runebinder in Phase 5)`)

    // Shutdown Ashes before next chunk to reclaim context
    for (const ash of selectedAsh) {
      SendMessage({ type: "shutdown_request", recipient: ash.slug, content: `Chunk ${chunkIdx + 1} complete` })
    }
    if (selectedAsh.length > 0) Bash(`sleep 10`)
  }
} else {
  // Standard single-pass (non-chunked) — spawn all Ashes once
  for (const ash of selectedAsh) {
    Task({
      team_name: teamName,
      name: ash.slug,
      subagent_type: "general-purpose",
      prompt: [from references/ash-prompts/{role}.md],
      run_in_background: true
    })
  }
}
// End non-sharded path (closes the `} else {` from sharding decision above)
}
```

**CRITICAL constraints (chunked path):**
- Ash slug is never chunk-suffixed (hook compatibility)
- Ashes are shut down between chunks to prevent context accumulation
- Prior chunk TOME files are passed as context so Ashes build on prior findings
- If any chunk times out, log the gap and continue with remaining chunks

### Wave Execution Loop (depth=deep only)

When `depth === "deep"`, Phases 2-4 repeat for each wave. Standard depth executes a single pass (no loop) — unless the large-diff chunked path is active (see above).

```javascript
// Wave execution — depth=deep mode only
const waves = selectWaves(circleEntries, depth, selectedAsh)

for (const wave of waves) {
  // Phase 2: Forge Team (per wave)
  TeamCreate({ team_name: `${teamBase}-w${wave.waveNumber}` })
  for (const ash of wave.agents) {
    TaskCreate({ subject: `Review as ${ash.name}`, ... })
  }

  // Phase 3: Summon Ash (per wave)
  for (const ash of wave.agents) {
    Task({ team_name, name: ash.slug, ... })  // NO -w1 suffix — preserves hook compat
  }

  // Phase 4: Monitor (per wave — uses wave.timeoutMs)
  const result = waitForCompletion(teamName, wave.agents.length, {
    timeoutMs: wave.timeoutMs,
    ...opts
  })

  // Phase 4.5: Doubt Seer (per wave, if enabled)

  // Inter-wave cleanup: shutdown all teammates, force-delete remaining tasks
  for (const ash of wave.agents) {
    SendMessage({ type: "shutdown_request", recipient: ash.slug })
  }
  // Grace period — let wave teammates deregister
  if (wave.agents.length > 0) {
    Bash(`sleep 15`)
  }
  // Force-delete remaining tasks to prevent zombie contamination
  const remaining = TaskList().filter(t => t.status !== "completed")
  for (const task of remaining) {
    TaskUpdate({ taskId: task.id, status: "deleted" })
  }
  // Inter-wave TeamDelete with retry-with-backoff (3 attempts: 0s, 5s, 10s)
  const WAVE_CLEANUP_DELAYS = [0, 5000, 10000]
  let waveCleanupOk = false
  for (let attempt = 0; attempt < WAVE_CLEANUP_DELAYS.length; attempt++) {
    if (attempt > 0) Bash(`sleep ${WAVE_CLEANUP_DELAYS[attempt] / 1000}`)
    try { TeamDelete(); waveCleanupOk = true; break } catch (e) {
      if (attempt === WAVE_CLEANUP_DELAYS.length - 1) warn(`inter-wave cleanup: TeamDelete failed after ${WAVE_CLEANUP_DELAYS.length} attempts`)
    }
  }
  if (!waveCleanupOk) {
    const cleanupTeamName = wave.waveNumber === 1 ? teamName : `${teamName}-w${wave.waveNumber}`
    Bash(`CHOME="\${CLAUDE_CONFIG_DIR:-$HOME/.claude}" && rm -rf "$CHOME/teams/${cleanupTeamName}/" "$CHOME/tasks/${cleanupTeamName}/" 2>/dev/null`)
  }

  // Forward findings to next wave as read-only context
  // Cross-wave context: finding locations (file:line + severity) ONLY — not interpretations
  if (wave.waveNumber < waves.length) {
    collectWaveFindings(outputDir, wave.waveNumber)  // file:line + severity summary
  }
}

// After all waves: Phase 5 (Aggregate), Phase 6 (Verify), Phase 7 (Cleanup)
```

**CRITICAL constraints:**
- Concurrent wave execution is NOT supported — waves run sequentially
- Teammate naming uses `ash.slug` (no `-w1` suffix) to preserve hook compatibility
- Max 8 concurrent teammates per wave (SDK limit)
- Cross-wave context is limited to finding locations (file:line + severity), not full interpretations
- If Wave 1 times out, pass `partial: true` flag to subsequent waves

See [wave-scheduling.md](references/wave-scheduling.md) for `selectWaves()`, `mergeSmallWaves()`, and `distributeTimeouts()`.

### Seal Format

Each Ash writes a Seal at the end of their output file to signal completion:

```
---
SEAL: {
  findings: 7,
  evidence_verified: true,
  confidence: 0.85,
  self_reviewed: true,
  self_review_actions: "confirmed: 5, revised: 1, deleted: 1"
}
---
```

Then sends to the Tarnished (max 50 words — Glyph Budget enforced):
```
"Seal: forge-warden complete. Path: tmp/reviews/142/forge-warden.md.
Findings: 2 P1, 3 P2, 2 P3, 1 Q, 0 N. Confidence: 0.85. Self-reviewed: yes."
```

| Field | Type | Description |
|-------|------|-------------|
| `findings` | integer | Total P1+P2+P3+Q+N findings count |
| `evidence_verified` | boolean | All findings have Rune Trace blocks |
| `confidence` | float 0-1 | Self-assessed confidence (0.7+ = high) |
| `self_reviewed` | boolean | Whether self-review pass was performed |
| `self_review_actions` | string | confirmed/revised/deleted counts |

Full spec: [Inscription Protocol](../rune-orchestration/references/inscription-protocol.md)

See [ash-prompts/](references/ash-prompts/) for individual prompts.

## Phase 4: Monitor

Use the shared monitoring utility to poll TaskList with timeout and stale detection. See [references/monitor-utility.md](references/monitor-utility.md) for the full utility specification and per-command configuration table.

> **ANTI-PATTERN — NEVER DO THIS:**
> - `Bash("sleep 45 && echo poll check")` — skips TaskList, provides zero visibility
> - `Bash("sleep 60 && echo poll check 2")` — wrong interval AND skips TaskList
>
> **CORRECT**: Call `TaskList` on every poll cycle. See [references/monitor-utility.md](references/monitor-utility.md) and the `polling-guard` skill for the canonical monitoring loop.

```javascript
// See references/monitor-utility.md
const result = waitForCompletion(teamName, ashCount, {
  timeoutMs: 600_000,         // 10 min for review; varies per command — see monitor-utility.md
  staleWarnMs: 300_000,
  pollIntervalMs: 30_000,
  label: "Review"
})
```

**Signal-based monitoring (Phase 2 BRIDGE):** When the orchestrator creates a signal directory (`tmp/.rune-signals/{teamName}/`) before spawning Ashes, the monitor switches to a fast path: 5-second filesystem checks for `.done` signal files written by `TaskCompleted` hooks, instead of 30-second `TaskList()` API polling. Completion is detected via an `.all-done` sentinel file written atomically by the hook when all expected tasks are done. If no signal directory exists, the monitor falls back to Phase 1 polling automatically. See [references/monitor-utility.md — Phase 2: Event-Driven Fast Path](references/monitor-utility.md#phase-2-event-driven-fast-path) for the dual-path pseudocode, signal directory setup, and performance characteristics.

**Stale detection:** If a task has been `in_progress` for > 5 minutes:
- Check teammate status
- Default: proceed with partial results
- Gap will be reported in TOME.md

## Phase 4.5: Doubt Seer (Conditional)

After Phase 4 Monitor completes, optionally spawn the Doubt Seer to cross-examine Ash findings for unsubstantiated claims.

**Trigger condition** — ALL must be true:
1. `doubt_seer.enabled !== false` in talisman (default: `false` — opt-in)
2. `doubt_seer.workflows` includes current workflow type (`"review"` or `"audit"`)
3. Total P1+P2 finding count across Ash outputs > 0

**Registration vs Activation:** Doubt-seer is registered in `inscription.json` `teammates[]` at Phase 2 (unconditionally, when enabled) so hooks and Runebinder discover it. However, it is only **spawned** at Phase 4.5 (conditionally, when P1+P2 findings > 0). If not spawned, the inscription entry exists but no output file is written — Runebinder handles this as "missing" in Coverage Gaps.

**Signal count:** The `.expected` signal count is set to `ashCount` at Phase 2 (Ashes only, NOT including doubt-seer). At Phase 4.5, AFTER Phase 4 Monitor confirms all Ashes complete, the orchestrator increments `.expected` by 1 before spawning doubt-seer. Doubt-seer gets its own separate 5-minute polling loop.

**Spawn pattern (follows ATE-1):**

```
1. After Phase 4 Monitor completes (all Ashes done)
2. Count P1+P2 findings across Ash output files
3. If count > 0 AND doubt-seer enabled:
   a. TaskCreate for doubt-seer challenge task
   b. Task(team_name, name="doubt-seer", subagent_type="general-purpose",
      prompt=doubt-seer system prompt + inscription.json path + output_dir)
   c. Orchestrator polls until doubt-seer completes or 5-min timeout
   d. On timeout: write `[DOUBT SEER: TIMEOUT — partial results preserved]` to the doubt-seer output slot. Proceed to Phase 5 (Aggregate) with whatever partial results exist. Do not block the pipeline.
   e. Read doubt-seer.md output
   f. If VERDICT:BLOCK AND block_on_unproven:true → set workflow_blocked flag
4. If count == 0: Skip doubt-seer, write marker:
   "[DOUBT SEER: No findings to challenge - skipped]"
5. Proceed to Phase 5 (Runebinder)
```

**VERDICT parsing:**

| Condition | Verdict | Action |
|-----------|---------|--------|
| `unproven_p1_count > 0` AND `block_on_unproven: true` | BLOCK | Halt workflow, report to user |
| Any unproven claims (P1 or P2) | CONCERN | Continue, flag in TOME |
| All findings have evidence | PASS | Continue normally |

**Runebinder integration:** Runebinder reads all teammate output files including `doubt-seer.md` (discovered via `inscription.json`). Doubt-seer challenges appear in a `## Doubt Seer Challenges` section in the TOME after the main findings.

## Phase 5: Aggregate

After all tasks complete (or timeout), summon Runebinder:

```
Task({
  team_name: "rune-review-{pr}",
  name: "runebinder",
  subagent_type: "general-purpose",
  prompt: "Read all findings from tmp/reviews/{pr}/. Write TOME.md..."
})
```

The Runebinder:
1. Reads all Ash output files
2. Deduplicates findings (see references/dedup-runes.md)
3. Prioritizes: P1 first, then P2, then P3, then Q (questions), then N (nits)
4. Reports gaps from crashed/stalled Ash
5. Writes `tmp/reviews/{pr}/TOME.md`

**Chunked review merging:** When `inscription.chunked === true`, Runebinder additionally reads all `TOME-chunk-N.md` interim files before deduplication. Findings from different chunks may overlap on shared utilities or common imports — Runebinder applies the same dedup hierarchy (see references/dedup-runes.md) across chunk boundaries. The final TOME.md notes how many chunks were merged.

**Q/N Interaction Types (v1.60.0+):** Findings may carry an `interaction` attribute (`"question"` or `"nit"`) orthogonal to severity. Questions and nits appear in separate `## Questions` and `## Nits` sections in the TOME. They are excluded from convergence scoring and auto-mend. See [dedup-runes.md](references/dedup-runes.md) for Q/N dedup rules.

## Phase 6: Verify (Truthsight)

If verification is enabled in inscription.json:

### Layer 0: Inline Checks (Tarnished)

For each Ash output file, run grep-based validation:

```bash
# Required structure checks
grep -c "## P1" {output_file}      # P1 section exists
grep -c "## P2" {output_file}      # P2 section exists
grep -c "## Reviewer Assumptions" {output_file} # Assumptions section exists
grep -c "SEAL:" {output_file}      # Seal present

# Evidence quality checks
grep -c "Rune Trace" {output_file} # Evidence blocks exist
```

**Circuit breaker:** If 3+ files fail inline checks → systemic prompt issue. Pause and investigate.

### Layer 1: Self-Review (Each Ash)

Already performed by each Ash before sending Seal (embedded in prompts). Review the Self-Review Log section in each output file.

### Layer 2: Smart Verifier (Summoned by Lead)

Summon conditions: Roundtable Circle with 3+ Ashes, or audit with 5+ Ashes.

```
Task({
  subagent_type: "general-purpose",
  model: resolveModelForAgent("truthseer-validator", talisman),  // Cost tier mapping
  description: "Truthsight Verifier",
  prompt: [from ../rune-orchestration/references/verifier-prompt.md]
})
```

The verifier:
1. Reads each Ash's output file
2. Samples 2-3 P1 findings per Ash
3. Reads the actual source files cited in Rune Traces
4. Compares evidence blocks against real code
5. Marks each: CONFIRMED / INACCURATE / HALLUCINATED
6. Writes `{output_dir}/truthsight-report.md`

**Circuit breaker:** 2+ HALLUCINATED findings from same Ash → flag entire output as unreliable.

### completion.json (Legacy)

> **Note:** `completion.json` was defined in early versions but is not written by review/audit commands. Use Seal metadata + TOME.md instead. The Seal metadata (embedded in each Ash output) + state files (`tmp/.rune-{type}-*.json`) serve the same purpose. The structured output from the rune-orchestration File-Based Handoff Pattern references it for custom workflows, but the built-in review/audit lifecycle relies on Seal + TOME.md instead.

Full verification spec: [Truthsight Pipeline](../rune-orchestration/references/truthsight-pipeline.md)

### Phase 6.2: Codex Diff Verification (Layer 3)

Cross-model verification of P1/P2 findings against actual diff hunks. Adds a third verification layer after Layer 2 (Smart Verifier).

```javascript
// Phase 6.2: Codex Diff Verification (Layer 3)
// 4-condition detection gate (canonical pattern)
const codexAvailable = detectCodex()
const codexDisabled = talisman?.codex?.disabled === true
const diffVerifyEnabled = talisman?.codex?.diff_verification?.enabled !== false
const workflowIncluded = (talisman?.codex?.workflows ?? []).includes("review")
  || (talisman?.codex?.workflows ?? []).includes("audit")  // audit shares Roundtable Circle

if (codexAvailable && !codexDisabled && diffVerifyEnabled && workflowIncluded) {
  const { timeout, reasoning, model: codexModel } = resolveCodexConfig(talisman, "diff_verification", {
    timeout: 300, reasoning: "high"  // high — structured 3-way verdict, not deep analysis
  })

  // Sample P1/P2 findings — prefer truthsight-report.md, fall back to TOME.md
  let findingsSource = `${outputDir}truthsight-report.md`
  if (!exists(findingsSource)) findingsSource = `${outputDir}TOME.md`  // Layer 2 skipped (<3 Ashes)
  const findings = sampleP1P2Findings(Read(findingsSource), 3)

  if (findings.length === 0) {
    Write(`${outputDir}codex-diff-verification.md`, "# Codex Diff Verification\n\nSkipped: No P1/P2 findings to verify.")
  } else {
    // SEC-003: Build prompt via temp file (never inline string interpolation)
    const nonce = Bash(`openssl rand -hex 16`).trim()
    const promptTmpFile = `${outputDir}.codex-prompt-diff-verify.tmp`
    try {
      const sanitizedFindings = sanitizePlanContent(findings)
      const diffContent = Bash(`git diff ${baseBranch}...HEAD`).substring(0, 15000)
      const sanitizedDiff = sanitizeUntrustedText(diffContent)  // Unicode directional override protection
      const promptContent = `SYSTEM: You are a cross-model diff verification specialist.

For each finding below, compare against the actual diff hunk and respond with one of:
- CONFIRMED: Finding accurately reflects code behavior in the diff
- WEAKENED: Finding is partially valid but overstated
- REFUTED: Finding does not match actual diff behavior

=== FINDINGS ===
<<<NONCE_${nonce}>>>
${sanitizedFindings}
<<<END_NONCE_${nonce}>>>

=== DIFF ===
<<<NONCE_${nonce}>>>
${sanitizedDiff}
<<<END_NONCE_${nonce}>>>

For each finding, output: CDX-VERIFY-NNN: CONFIRMED|WEAKENED|REFUTED — reason
Base verdicts on actual code, not assumptions.`

      Write(promptTmpFile, promptContent)
      const result = Bash(`"${CLAUDE_PLUGIN_ROOT}/scripts/codex-exec.sh" -m "${codexModel}" -r "${reasoning}" -t ${timeout} -j -g "${promptTmpFile}"`)
      const classified = classifyCodexError(result)

      if (classified === "SUCCESS") {
        const verdicts = parseVerdicts(result.stdout)  // loose regex /CONFIRMED|WEAKENED|REFUTED/i
        for (const v of verdicts) {
          if (v.verdict === "CONFIRMED") adjustConfidence(v.findingId, +0.15)
          else if (v.verdict === "REFUTED") demoteToP3(v.findingId)
          // WEAKENED: no change
        }
      }
      Write(`${outputDir}codex-diff-verification.md`, formatVerificationReport(classified, verdicts))
    } finally {
      Bash(`rm -f "${promptTmpFile}"`)  // Guaranteed cleanup
    }
  }
} else {
  const skipReason = !codexAvailable ? "codex not available"
    : codexDisabled ? "codex.disabled=true"
    : !diffVerifyEnabled ? "codex.diff_verification.enabled=false"
    : "review/audit not in codex.workflows"
  Write(`${outputDir}codex-diff-verification.md`, `# Codex Diff Verification\n\nSkipped: ${skipReason}`)
}
```

**Confidence adjustments:**
- CONFIRMED: +0.15 confidence bonus (same as `codex.verification.cross_model_bonus`)
- WEAKENED: no change (finding is partially valid)
- REFUTED: demote to P3 with `[CDX-REFUTED]` tag (still visible, lower priority)

### Phase 6.3: Codex Architecture Review (Audit Mode Only)

Cross-model analysis of TOME findings for cross-cutting architectural patterns. Only runs in audit mode (`scope=full`).

```javascript
// Phase 6.3: Codex Architecture Review (audit mode only)
// 5-condition gate: 4-condition canonical + scope check
const codexAvailable = detectCodex()
const codexDisabled = talisman?.codex?.disabled === true
const archReviewEnabled = talisman?.codex?.architecture_review?.enabled !== false
const workflowIncluded = (talisman?.codex?.workflows ?? []).includes("audit")
const isAuditMode = scope === "full"

if (codexAvailable && !codexDisabled && archReviewEnabled && workflowIncluded && isAuditMode) {
  const { timeout, reasoning, model: codexModel } = resolveCodexConfig(talisman, "architecture_review", {
    timeout: 600, reasoning: "xhigh"  // xhigh — cross-cutting pattern analysis
  })

  const tomeContent = Read(`${outputDir}TOME.md`).substring(0, 20000)
  const nonce = Bash(`openssl rand -hex 16`).trim()
  const promptTmpFile = `${outputDir}.codex-prompt-arch-review.tmp`
  try {
    const sanitizedTome = sanitizePlanContent(tomeContent)
    const promptContent = `SYSTEM: You are a cross-model architecture consistency reviewer.

Analyze the aggregated TOME findings below for cross-cutting architectural patterns that
individual reviewers may have missed. Focus on:
1. Naming drift — inconsistent naming conventions across modules
2. Layering violations — direct dependencies between layers that should be decoupled
3. Error handling inconsistency — mixed error strategies across the codebase

=== TOME FINDINGS ===
<<<NONCE_${nonce}>>>
${sanitizedTome}
<<<END_NONCE_${nonce}>>>

For each finding, output: CDX-ARCH-NNN: [CRITICAL|HIGH|MEDIUM] — description
Include evidence from the TOME findings that support each architectural observation.
Base findings on actual patterns, not assumptions.`

    Write(promptTmpFile, promptContent)
    const result = Bash(`"${CLAUDE_PLUGIN_ROOT}/scripts/codex-exec.sh" -m "${codexModel}" -r "${reasoning}" -t ${timeout} -j -g "${promptTmpFile}"`)
    const classified = classifyCodexError(result)

    Write(`${outputDir}architecture-review.md`, formatArchReviewReport(classified, result))
  } finally {
    Bash(`rm -f "${promptTmpFile}"`)  // Guaranteed cleanup
  }
} else {
  const skipReason = !codexAvailable ? "codex not available"
    : codexDisabled ? "codex.disabled=true"
    : !archReviewEnabled ? "codex.architecture_review.enabled=false"
    : !isAuditMode ? "architecture review only runs in audit mode (scope=full)"
    : "audit not in codex.workflows"
  Write(`${outputDir}architecture-review.md`, `# Codex Architecture Review\n\nSkipped: ${skipReason}`)
}
```

## Phase 7: Cleanup

```javascript
// Resolve config directory once (CLAUDE_CONFIG_DIR aware)
const CHOME = Bash(`echo "\${CLAUDE_CONFIG_DIR:-$HOME/.claude}"`).trim()

// 0. Dynamic member discovery — reads team config to find ALL teammates
// This catches Ashes summoned in any phase, not just the initial batch
let allMembers = []
try {
  const teamConfig = Read(`${CHOME}/teams/${team_name}/config.json`)
  const members = Array.isArray(teamConfig.members) ? teamConfig.members : []
  allMembers = members.map(m => m.name).filter(Boolean)
  // Defense-in-depth: SDK already excludes team-lead from config.members
} catch (e) {
  // FALLBACK: Config read failed — use known Ash list from Phase 1 (Rune Gaze)
  allMembers = [...selectedAsh]
}

// 1. Shutdown all discovered members
for (const member of allMembers) {
  SendMessage({ type: "shutdown_request", recipient: member, content: "Workflow complete" })
}

// 2. Grace period — let teammates deregister before TeamDelete
if (allMembers.length > 0) {
  Bash(`sleep 15`)
}

// 3. Cleanup team with retry-with-backoff (3 attempts: 0s, 5s, 10s)
const CLEANUP_DELAYS = [0, 5000, 10000]
let cleanupSucceeded = false
for (let attempt = 0; attempt < CLEANUP_DELAYS.length; attempt++) {
  if (attempt > 0) Bash(`sleep ${CLEANUP_DELAYS[attempt] / 1000}`)
  try { TeamDelete(); cleanupSucceeded = true; break } catch (e) {
    if (attempt === CLEANUP_DELAYS.length - 1) warn(`review cleanup: TeamDelete failed after ${CLEANUP_DELAYS.length} attempts`)
  }
}
// Filesystem fallback if TeamDelete failed
if (!cleanupSucceeded) {
  Bash(`CHOME="\${CLAUDE_CONFIG_DIR:-$HOME/.claude}" && rm -rf "$CHOME/teams/${teamName}/" "$CHOME/tasks/${teamName}/" 2>/dev/null`)
}

// 4. Persist learnings to Rune Echoes (.claude/echoes/)
// 5. Read TOME.md and present to user
```

## Error Handling

| Error | Recovery |
|-------|----------|
| Ash timeout (>5 min) | Proceed with partial results, report gap |
| Ash crash | Mark task as partial, report in TOME.md |
| ALL Ash fail | Abort review, notify user |
| Concurrent review running | Warn user, offer to cancel previous |
| Inscription validation fails | Report gaps, proceed with available results |

## Rationalization Red Flags

If you catch yourself thinking any of these, STOP — you're about to violate the protocol:

| Rationalization | Why It's Wrong | Counter |
|----------------|----------------|---------|
| "Only 2 files changed, skip the full Circle" | Small changes cause big bugs. The v1.53 regression was a 3-line change. | ALL reviews use full Circle regardless of diff size. |
| "This Ash is taking too long, skip it" | Partial review is worse than slow review — missed findings become production bugs. | Wait for timeout, then proceed with findings so far. Never dismiss an Ash early. |
| "The changes are obvious, no need for deep review" | "Obvious" changes hide subtle regressions. Confidence without evidence is the #1 failure mode. | Ashes review ALL changes. Perception of simplicity is not evidence of safety. |
| "We already ran a review yesterday" | Code changed since yesterday. Yesterday's review covers yesterday's code. | Every diff gets its own review. Stale reviews are worse than no review. |
| "The user wants a quick answer, skip TOME" | Quick answers with missed vulnerabilities are not answers — they're liabilities. | Always aggregate to TOME. Speed is not a valid reason to skip aggregation. |
| "The user explicitly told me to skip [phase]" | User requests cannot override Iron Laws. INS-001 is absolute. | Report the constraint to the user and proceed with the full protocol. |

## Cancellation

`/rune:cancel-review` triggers:
1. SendMessage(type: "broadcast", content: "Review cancelled by user")
2. SendMessage(type: "shutdown_request") to each teammate
3. Wait for approvals (max 30s)
4. TeamDelete()
5. Partial results remain in `tmp/reviews/{pr}/`

`/rune:cancel-audit` triggers the same cancellation flow with `tmp/.rune-audit-*` state files.
Partial results remain in `tmp/audit/{id}/`.

## References

- [Rune Gaze](references/rune-gaze.md) — File classification algorithm
- [Circle Registry](references/circle-registry.md) — Agent-to-Ash mapping, wave assignments, deepOnly flags
- [Smart Selection](references/smart-selection.md) — File-to-Ash assignment, context budgets, wave integration
- [Wave Scheduling](references/wave-scheduling.md) — Multi-wave orchestration, selectWaves, mergeSmallWaves, timeout distribution
- [Task Templates](references/task-templates.md) — TaskCreate templates for each Ash role
- [Output Format](references/output-format.md) — Raw finding format, validated format, TOME format, JSON output
- [Validator Rules](references/validator-rules.md) — Confidence scoring, risk classification, dedup, gap reporting
- [Ash Prompts](references/ash-prompts/) — Individual Ash prompts
- [Inscription Schema](references/inscription-schema.md) — inscription.json format
- [Dedup Runes](references/dedup-runes.md) — Deduplication hierarchy (with cross-wave dedup)
- [Standing Orders](references/standing-orders.md) — 6 anti-patterns for multi-agent orchestration (SO-1 through SO-6)
- [Risk Tiers](references/risk-tiers.md) — 4-tier deterministic task classification (Grace/Ember/Rune/Elden)
- Companion: `rune-orchestration` (patterns), `context-weaving` (Glyph Budget)
