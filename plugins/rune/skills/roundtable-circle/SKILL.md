---
name: roundtable-circle
description: |
  Orchestrates multi-agent code reviews using Agent Teams with up to 8 Ashes teammates (5 built-in + custom).
  This skill should be used when running /rune:review or /rune:audit. Each Ash gets its own 200k context window.
  Handles scope selection, team creation, inscription generation, Ash summoning, monitoring, aggregation, verification, and cleanup.

  <example>
  Context: Running a code review
  user: "/rune:review"
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

Orchestrates multi-agent code reviews using Claude Code Agent Teams. Each Ash teammate gets its own 200k context window, eliminating single-context bottlenecks.

## Architecture

### 7-Phase Lifecycle

```
Phase 0: Pre-flight     → Validate git status, check for changes
Phase 1: Rune Gaze      → git diff → classify files → select Ash
Phase 2: Forge Team      → TeamCreate + TaskCreate + inscription.json
Phase 3: Summon           → Fan-out Ash with self-organizing prompts
Phase 4: Monitor         → TaskList polling, 5-min stale detection
Phase 5: Aggregate       → Summon Runebinder → writes TOME.md
Phase 6: Verify          → Truthsight validation on P1 findings
Phase 7: Cleanup         → Shutdown requests → approvals → TeamDelete
```

### Built-in Ash Roles (Max 5)

| Ash | Role | When Selected | Perspectives |
|-----------|------|---------------|-------------|
| **Forge Warden** | Backend review | Backend files changed | Architecture, performance, logic bugs, duplication |
| **Ward Sentinel** | Security review | ALWAYS | Vulnerabilities, auth, injection, OWASP |
| **Pattern Weaver** | Quality patterns | ALWAYS | Simplicity, TDD, dead code, pattern consistency |
| **Glyph Scribe** | Frontend review | Frontend files changed | TypeScript safety, React performance, accessibility |
| **Knowledge Keeper** | Docs review | Docs changed (>= 10 lines) | Accuracy, completeness, anti-injection |

Plus **Runebinder** (utility) for aggregation in Phase 5.

### Custom Ashes (Extensible)

Projects can register additional Ash from local agents, global agents, or other plugins via `talisman.yml`. Custom Ashes join the standard lifecycle:

- **Wrapped** with Truthbinding Protocol (evidence, Glyph Budget, Seal format)
- **Summoned** alongside built-ins in Phase 3 (parallel execution)
- **Deduplicated** using their unique `finding_prefix` in the extended hierarchy
- **Verified** by Truthsight (if `settings.verification.layer_2_custom_agents: true`)
- **Aggregated** into TOME.md by Runebinder

**Max total:** 5 built-in + up to 3 custom = 8 Ashes (configurable via `settings.max_ashes`). The cap exists because each Ash output (~10k tokens) consumes verifier context budget.

See [`custom-ashes.md`](references/custom-ashes.md) for full schema, wrapper prompt template, and examples.

### Output Directory Structure

```
tmp/reviews/{id}/
├── inscription.json         # Output contract (generated Phase 2)
├── forge-warden.md          # Backend review findings
├── ward-sentinel.md         # Security review findings
├── pattern-weaver.md        # Quality patterns findings
├── glyph-scribe.md          # Frontend review findings (if summoned)
├── knowledge-keeper.md      # Docs review findings (if summoned)
├── TOME.md                  # Aggregated + deduplicated findings
├── truthsight-report.md     # Verification results (if Layer 2 enabled)
└── completion.json          # Structured completion summary
```

### Audit Mode

`/rune:audit` reuses the same 7-phase lifecycle with one difference in Phase 0:

| Aspect | Review (`/rune:review`) | Audit (`/rune:audit`) |
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
# Check for changes to review
git diff --name-only HEAD~1..HEAD
# OR for PRs:
git diff --name-only main..HEAD
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

## Phase 2: Forge Team

```
1. mkdir -p tmp/reviews/{pr-number}/
2. Generate inscription.json (see references/inscription-schema.md)
3. TeamCreate({ team_name: "rune-review-{pr}" })
4. For each selected Ash:
   TaskCreate({
     subject: "Review {scope} as {role}",
     description: "Files: [...], Output: tmp/reviews/{pr}/{role}.md"
   })
```

## Phase 3: Summon Ash

For each selected Ash, summon as a background teammate:

```
Task({
  team_name: "rune-review-{pr}",
  name: "{ash-name}",
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
Findings: 2 P1, 3 P2, 2 P3. Confidence: 0.85. Self-reviewed: yes."
```

| Field | Type | Description |
|-------|------|-------------|
| `findings` | integer | Total P1+P2+P3 findings count |
| `evidence_verified` | boolean | All findings have Rune Trace blocks |
| `confidence` | float 0-1 | Self-assessed confidence (0.7+ = high) |
| `self_reviewed` | boolean | Whether self-review pass was performed |
| `self_review_actions` | string | confirmed/revised/deleted counts |

Full spec: [Inscription Protocol](../rune-orchestration/references/inscription-protocol.md)

See `references/ash-prompts/` for individual prompts.

## Phase 4: Monitor

Poll TaskList every 30 seconds:

```
while (not all tasks completed):
  tasks = TaskList()
  for task in tasks:
    if task.status == "completed":
      continue
    if task.stale > 5 minutes:
      warn("Ash {name} may be stalled")
  sleep(30)
```

**Stale detection:** If a task has been `in_progress` for > 5 minutes:
- Check teammate status
- Default: proceed with partial results
- Gap will be reported in TOME.md

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
3. Prioritizes: P1 first, then P2, then P3
4. Reports gaps from crashed/stalled Ash
5. Writes `tmp/reviews/{pr}/TOME.md`

## Phase 6: Verify (Truthsight)

If verification is enabled in inscription.json:

### Layer 0: Inline Checks (Tarnished)

For each Ash output file, run grep-based validation:

```bash
# Required structure checks
grep -c "## P1" {output_file}      # P1 section exists
grep -c "## P2" {output_file}      # P2 section exists
grep -c "## Summary" {output_file} # Summary section exists
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
  model: "haiku",
  description: "Truthsight Verifier",
  prompt: [from rune-orchestration/references/verifier-prompt.md]
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

### completion.json

After verification, write structured completion summary:

```json
{
  "workflow": "rune-review",
  "identifier": "PR #142",
  "completed_at": "2026-02-11T11:00:00Z",
  "ash": {
    "forge-warden": { "status": "complete", "findings": 7, "confidence": 0.85 },
    "ward-sentinel": { "status": "complete", "findings": 3, "confidence": 0.90 },
    "pattern-weaver": { "status": "partial", "findings": 2, "confidence": 0.60 }
  },
  "aggregation": { "tome_path": "tmp/reviews/142/TOME.md", "total_findings": 12 },
  "verification": { "layer_0_passed": true, "layer_2_hallucinated": 0 }
}
```

Full verification spec: [Truthsight Pipeline](../rune-orchestration/references/truthsight-pipeline.md)

## Phase 7: Cleanup

```
1. SendMessage(type: "shutdown_request") to each Ash
2. Wait for shutdown approvals
3. TeamDelete()
4. Read TOME.md and present to user
```

## Error Handling

| Error | Recovery |
|-------|----------|
| Ash timeout (>5 min) | Proceed with partial results, report gap |
| Ash crash | Mark task as partial, report in TOME.md |
| ALL Ash fail | Abort review, notify user |
| Concurrent review running | Warn user, offer to cancel previous |
| Inscription validation fails | Report gaps, proceed with available results |

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
- [Circle Registry](references/circle-registry.md) — Agent-to-Ash mapping, audit scope priorities, focus mode
- [Smart Selection](references/smart-selection.md) — File-to-Ash assignment, context budgets, focus mode
- [Task Templates](references/task-templates.md) — TaskCreate templates for each Ash role
- [Output Format](references/output-format.md) — Raw finding format, validated format, TOME format, JSON output
- [Validator Rules](references/validator-rules.md) — Confidence scoring, risk classification, dedup, gap reporting
- [Ash Prompts](references/ash-prompts/) — Individual Ash prompts
- [Inscription Schema](references/inscription-schema.md) — inscription.json format
- [Dedup Runes](references/dedup-runes.md) — Deduplication hierarchy
- Companion: `rune-orchestration` (patterns), `context-weaving` (Glyph Budget)
