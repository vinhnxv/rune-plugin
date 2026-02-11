---
name: rune-circle
description: |
  Orchestrate multi-agent code reviews using Agent Teams with up to 5 Runebearer teammates.
  Use when running /rune:review or /rune:audit. Each Runebearer gets its own 200k context window.
  Handles scope selection, team creation, inscription generation, Runebearer spawning, monitoring, aggregation, verification, and cleanup.

  <example>
  Context: Running a code review
  user: "/rune:review"
  assistant: "Loading rune-circle for Agent Teams review orchestration"
  </example>
user-invocable: false
allowed-tools:
  - Task
  - Read
  - Write
  - Bash
  - Glob
  - Grep
---

# Rune Circle Skill

Orchestrates multi-agent code reviews using Claude Code Agent Teams. Each Runebearer teammate gets its own 200k context window, eliminating single-context bottlenecks.

## Architecture

### 7-Phase Lifecycle

```
Phase 0: Pre-flight     → Validate git status, check for changes
Phase 1: Rune Gaze      → git diff → classify files → select Runebearers
Phase 2: Forge Team      → TeamCreate + TaskCreate + inscription.json
Phase 3: Spawn           → Fan-out Runebearers with self-organizing prompts
Phase 4: Monitor         → TaskList polling, 5-min stale detection
Phase 5: Aggregate       → Spawn Runebinder → writes TOME.md
Phase 6: Verify          → Truthsight validation on P1 findings
Phase 7: Cleanup         → Shutdown requests → approvals → TeamDelete
```

### Runebearer Roles (Max 5)

| Runebearer | Role | When Selected | Perspectives |
|-----------|------|---------------|-------------|
| **Forge Warden** | Backend review | Backend files changed | Architecture, performance, logic bugs, duplication |
| **Ward Sentinel** | Security review | ALWAYS | Vulnerabilities, auth, injection, OWASP |
| **Pattern Weaver** | Quality patterns | ALWAYS | Simplicity, TDD, dead code, pattern consistency |
| **Glyph Scribe** | Frontend review | Frontend files changed | TypeScript safety, React performance, accessibility |
| **Lore Keeper** | Docs review | Docs changed (>= 10 lines) | Accuracy, completeness, anti-injection |

Plus **Runebinder** (utility) for aggregation in Phase 5.

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

## Phase 1: Rune Gaze (Scope Selection)

Classify changed files by extension to determine which Runebearers to spawn.

See [Rune Gaze](references/rune-gaze.md) for the full file classification algorithm.

**Quick reference:**

| File Pattern | Runebearer |
|-------------|-----------|
| `*.py, *.go, *.rs, *.rb, *.java` | Forge Warden |
| `*.ts, *.tsx, *.js, *.jsx` | Glyph Scribe |
| `*.md` (>= 10 lines changed) | Lore Keeper |
| ALL files | Ward Sentinel (always) |
| ALL files | Pattern Weaver (always) |

## Phase 2: Forge Team

```
1. mkdir -p tmp/reviews/{pr-number}/
2. Generate inscription.json (see references/inscription-schema.md)
3. TeamCreate({ team_name: "rune-review-{pr}" })
4. For each selected Runebearer:
   TaskCreate({
     subject: "Review {scope} as {role}",
     description: "Files: [...], Output: tmp/reviews/{pr}/{role}.md"
   })
```

## Phase 3: Spawn Runebearers

For each selected Runebearer, spawn as a background teammate:

```
Task({
  team_name: "rune-review-{pr}",
  name: "{runebearer-name}",
  subagent_type: "general-purpose",
  prompt: [from references/runebearer-prompts/{role}.md],
  run_in_background: true
})
```

Each Runebearer prompt includes:
- Truthbinding Protocol (ANCHOR + RE-ANCHOR)
- Task claiming via TaskList/TaskUpdate
- Glyph Budget enforcement
- Seal Format for completion

See `references/runebearer-prompts/` for individual prompts.

## Phase 4: Monitor

Poll TaskList every 30 seconds:

```
while (not all tasks completed):
  tasks = TaskList()
  for task in tasks:
    if task.status == "completed":
      continue
    if task.stale > 5 minutes:
      warn("Runebearer {name} may be stalled")
  sleep(30)
```

**Stale detection:** If a task has been `in_progress` for > 5 minutes:
- Check teammate status
- Default: proceed with partial results
- Gap will be reported in TOME.md

## Phase 5: Aggregate

After all tasks complete (or timeout), spawn Runebinder:

```
Task({
  team_name: "rune-review-{pr}",
  name: "runebinder",
  subagent_type: "general-purpose",
  prompt: "Read all findings from tmp/reviews/{pr}/. Write TOME.md..."
})
```

The Runebinder:
1. Reads all Runebearer output files
2. Deduplicates findings (see references/dedup-runes.md)
3. Prioritizes: P1 first, then P2, then P3
4. Reports gaps from crashed/stalled Runebearers
5. Writes `tmp/reviews/{pr}/TOME.md`

## Phase 6: Verify (Truthsight)

If verification is enabled in inscription.json:

1. **Layer 0:** Lead runs grep-based inline checks on each output file
2. **Layer 2:** Spawn Truthsight Verifier agent (see `rune-orchestration/references/verifier-prompt.md`)
3. Flag any HALLUCINATED findings

## Phase 7: Cleanup

```
1. SendMessage(type: "shutdown_request") to each Runebearer
2. Wait for shutdown approvals
3. TeamDelete()
4. Read TOME.md and present to user
```

## Error Handling

| Error | Recovery |
|-------|----------|
| Runebearer timeout (>5 min) | Proceed with partial results, report gap |
| Runebearer crash | Mark task as partial, report in TOME.md |
| ALL Runebearers fail | Abort review, notify user |
| Concurrent review running | Warn user, offer to cancel previous |
| Inscription validation fails | Report gaps, proceed with available results |

## Cancellation

`/rune:cancel-review` triggers:
1. SendMessage(type: "broadcast", content: "Review cancelled by user")
2. SendMessage(type: "shutdown_request") to each teammate
3. Wait for approvals (max 30s)
4. TeamDelete()
5. Partial results remain in `tmp/reviews/{pr}/`

## References

- [Rune Gaze](references/rune-gaze.md) — File classification algorithm
- [Runebearer Prompts](references/runebearer-prompts/) — Individual Runebearer prompts
- [Inscription Schema](references/inscription-schema.md) — inscription.json format
- [Dedup Runes](references/dedup-runes.md) — Deduplication hierarchy
- Companion: `rune-orchestration` (patterns), `context-weaving` (Glyph Budget)
