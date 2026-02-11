---
name: review
description: |
  Multi-agent code review using Agent Teams. Spawns up to 5 Runebearer teammates,
  each with their own 200k context window. Handles scope selection, team creation,
  review orchestration, aggregation, verification, and cleanup.

  <example>
  user: "/rune:review"
  assistant: "Starting Rune Circle review with Agent Teams..."
  </example>
user-invocable: true
allowed-tools:
  - Task
  - TaskCreate
  - TaskList
  - TaskUpdate
  - TeamCreate
  - TeamDelete
  - SendMessage
  - Read
  - Write
  - Bash
  - Glob
  - Grep
---

# /rune:review — Multi-Agent Code Review

Orchestrate a multi-agent code review using the Rune Circle architecture. Each Runebearer gets its own 200k context window via Agent Teams.

**Load skill**: `rune-circle` for full architecture reference.

## Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--partial` | Review only staged files (`git diff --cached`) instead of full branch diff | Off (reviews all branch changes) |
| `--dry-run` | Show scope selection and Runebearer plan without spawning agents | Off |

**Partial mode** is useful for reviewing a subset of changes before committing, rather than the full branch diff against the default branch.

**Dry-run mode** executes Phase 0 (Pre-flight) and Phase 1 (Rune Gaze) only, then displays:
- Changed files classified by type
- Which Runebearers would be spawned
- File assignments per Runebearer (with context budget caps)
- Estimated team size

No teams, tasks, or agents are created. Use this to preview scope before committing to a full review.

## Phase 0: Pre-flight

```bash
# Determine what to review
branch=$(git branch --show-current)
default_branch=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
if [ -z "$default_branch" ]; then
  default_branch=$(git rev-parse --verify origin/main >/dev/null 2>&1 && echo "main" || echo "master")
fi

# Get changed files
if [ "--partial" in flags ]; then
  # Partial mode: only staged files
  changed_files=$(git diff --cached --name-only)
else
  # Default: full branch diff
  changed_files=$(git diff --name-only ${default_branch}...HEAD)
fi
```

**Abort conditions:**
- No changed files → "Nothing to review. Make some changes first."
- Only non-reviewable files (images, lock files) → "No reviewable changes found."

## Phase 1: Rune Gaze (Scope Selection)

Classify changed files by extension. See `rune-circle/references/rune-gaze.md`.

```
for each file in changed_files:
  - *.py, *.go, *.rs, *.rb, *.java, etc. → select Forge Warden
  - *.ts, *.tsx, *.js, *.jsx, etc.       → select Glyph Scribe
  - *.md (>= 10 lines changed)            → select Lore Keeper
  - Always: Ward Sentinel (security)
  - Always: Pattern Weaver (quality)
```

Check for project overrides in `.claude/rune-config.yml`.

### Dry-Run Exit Point

If `--dry-run` flag is set, display the plan and stop:

```
Dry Run — Review Plan
━━━━━━━━━━━━━━━━━━━━━

Branch: {branch} (vs {default_branch})
Changed files: {count}
  Backend:  {count} files
  Frontend: {count} files
  Docs:     {count} files
  Other:    {count} files (skipped)

Runebearers to spawn: {count}
  - Forge Warden:   {file_count} files (cap: 30)
  - Ward Sentinel:  {file_count} files (cap: 20)
  - Pattern Weaver: {file_count} files (cap: 30)
  - Glyph Scribe:   {file_count} files (cap: 25)  [conditional]
  - Lore Keeper:    {file_count} files (cap: 25)  [conditional]

To run the full review: /rune:review
```

Do NOT proceed to Phase 2. Exit here.

## Phase 2: Forge Team

```javascript
// 1. Check for concurrent review
// If tmp/.rune-review-{identifier}.json exists and < 30 min old, abort

// 2. Create output directory
Bash("mkdir -p tmp/reviews/{identifier}")

// 3. Write state file
Write("tmp/.rune-review-{identifier}.json", {
  team_name: "rune-review-{identifier}",
  started: timestamp,
  status: "active",
  expected_files: selectedRunebearers.map(r => `tmp/reviews/${id}/${r}.md`)
})

// 4. Generate inscription.json (see rune-circle/references/inscription-schema.md)
Write("tmp/reviews/{identifier}/inscription.json", { ... })

// 5. Create team
TeamCreate({ team_name: "rune-review-{identifier}" })

// 6. Create tasks (one per Runebearer)
for (const runebearer of selectedRunebearers) {
  TaskCreate({
    subject: `Review as ${runebearer}`,
    description: `Files: [...], Output: tmp/reviews/{id}/${runebearer}.md`,
    activeForm: `${runebearer} reviewing...`
  })
}
```

## Phase 3: Spawn Runebearers

Spawn ALL selected Runebearers in a **single message** (parallel execution):

```javascript
// For each selected Runebearer, spawn as background teammate
Task({
  team_name: "rune-review-{identifier}",
  name: "{runebearer-name}",
  subagent_type: "general-purpose",
  prompt: /* Load from rune-circle/references/runebearer-prompts/{role}.md
             Substitute: {changed_files}, {output_path}, {task_id}, {branch}, {timestamp} */,
  run_in_background: true
})
```

**IMPORTANT**: The lead MUST NOT review code itself. Focus solely on coordination.

## Phase 4: Monitor

Poll TaskList every 30 seconds until all tasks complete:

```
while (not all tasks completed):
  tasks = TaskList()
  for task in tasks:
    if task.status == "completed": continue
    if task.stale > 5 minutes:
      warn("Runebearer may be stalled")
  sleep(30)
```

**Stale detection**: If a task is `in_progress` for > 5 minutes, proceed with partial results.

## Phase 5: Aggregate (Runebinder)

After all tasks complete (or timeout):

```javascript
Task({
  team_name: "rune-review-{identifier}",
  name: "runebinder",
  subagent_type: "general-purpose",
  prompt: `Read all findings from tmp/reviews/{id}/.
    Deduplicate using hierarchy: SEC > BACK > DOC > QUAL > FRONT.
    Write unified summary to tmp/reviews/{id}/TOME.md.
    See rune-circle/references/dedup-runes.md for dedup algorithm.`
})
```

## Phase 6: Verify (Truthsight)

If inscription.json has `verification.enabled: true`:

1. **Layer 0**: Lead runs grep-based inline checks (file paths exist, line numbers valid)
2. **Layer 2**: Spawn Truthsight Verifier for P1 findings (see `rune-orchestration/references/verifier-prompt.md`)
3. Flag any HALLUCINATED findings

## Phase 7: Cleanup & Echo Persist

```javascript
// 1. Shutdown all Runebearers
for (const runebearer of allRunebearers) {
  SendMessage({ type: "shutdown_request", recipient: runebearer })
}

// 2. Wait for shutdown approvals (max 30s)

// 3. Cleanup team
TeamDelete()

// 4. Persist learnings to Rune Echoes (if .claude/echoes/ exists)
//    Extract P1/P2 patterns from TOME.md and write as Inscribed entries
//    See rune-echoes skill for entry format and write protocol
if (exists(".claude/echoes/reviewer/")) {
  patterns = extractRecurringPatterns("tmp/reviews/{identifier}/TOME.md")
  for (const pattern of patterns) {
    appendEchoEntry("echoes/reviewer/MEMORY.md", {
      layer: "inscribed",
      source: `rune:review ${identifier}`,
      confidence: pattern.confidence,
      evidence: pattern.evidence,
      content: pattern.summary
    })
  }
}

// 5. Read and present TOME.md to user
Read("tmp/reviews/{identifier}/TOME.md")
```

## Error Handling

| Error | Recovery |
|-------|----------|
| Runebearer timeout (>5 min) | Proceed with partial results |
| Runebearer crash | Report gap in TOME.md |
| ALL Runebearers fail | Abort, notify user |
| Concurrent review running | Warn, offer to cancel previous |
