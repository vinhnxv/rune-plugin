---
name: rune:review
description: |
  Multi-agent code review using Agent Teams. Spawns up to 5 built-in Tarnished teammates
  (plus custom Tarnished from talisman.yml), each with their own 200k context window.
  Handles scope selection, team creation, review orchestration, aggregation, verification, and cleanup.

  <example>
  user: "/rune:review"
  assistant: "The Elden Lord convenes the Roundtable Circle for review..."
  </example>
user-invocable: true
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

# /rune:review — Multi-Agent Code Review

Orchestrate a multi-agent code review using the Roundtable Circle architecture. Each Tarnished gets its own 200k context window via Agent Teams.

**Load skill**: `roundtable-circle` for full architecture reference.

## Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--partial` | Review only staged files (`git diff --cached`) instead of full branch diff | Off (reviews all branch changes) |
| `--dry-run` | Show scope selection and Tarnished plan without spawning agents | Off |
| `--max-agents <N>` | Limit total Tarnished spawned (built-in + custom). Range: 1-8 | All selected |

**Partial mode** is useful for reviewing a subset of changes before committing, rather than the full branch diff against the default branch.

**Dry-run mode** executes Phase 0 (Pre-flight) and Phase 1 (Rune Gaze) only, then displays:
- Changed files classified by type
- Which Tarnished would be spawned
- File assignments per Tarnished (with context budget caps)
- Estimated team size

No teams, tasks, state files, or agents are created. Use this to preview scope before committing to a full review.

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

### Load Custom Tarnished

After collecting changed files, check for custom Tarnished config:

```
1. Read .claude/talisman.yml (project) or ~/.claude/talisman.yml (global)
2. If tarnished.custom[] exists:
   a. Validate: unique prefixes, unique names, resolvable agents, count ≤ max
   b. Filter by workflows: keep only entries with "review" in workflows[]
   c. Match triggers against changed_files (extension + path match)
   d. Skip entries with fewer matching files than trigger.min_files
3. Merge validated custom Tarnished with built-in selections
4. Apply defaults.disable_tarnished to remove any disabled built-ins
```

See `roundtable-circle/references/custom-tarnished.md` for full schema and validation rules.

## Phase 1: Rune Gaze (Scope Selection)

Classify changed files by extension. See `roundtable-circle/references/rune-gaze.md`.

```
for each file in changed_files:
  - *.py, *.go, *.rs, *.rb, *.java, etc. → select Forge Warden
  - *.ts, *.tsx, *.js, *.jsx, etc.       → select Glyph Scribe
  - *.md (>= 10 lines changed)            → select Knowledge Keeper
  - Always: Ward Sentinel (security)
  - Always: Pattern Weaver (quality)

# Custom Tarnished (from talisman.yml):
for each custom in validated_custom_tarnished:
  matching = files where extension in custom.trigger.extensions
                    AND (custom.trigger.paths is empty OR file starts with any path)
  if len(matching) >= custom.trigger.min_files:
    select custom.name with matching[:custom.context_budget]
```

Check for project overrides in `.claude/talisman.yml`.

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

Tarnished to spawn: {count} ({built_in_count} built-in + {custom_count} custom)
  Built-in:
  - Forge Warden:      {file_count} files (cap: 30)
  - Ward Sentinel:     {file_count} files (cap: 20)
  - Pattern Weaver:    {file_count} files (cap: 30)
  - Glyph Scribe:      {file_count} files (cap: 25)  [conditional]
  - Knowledge Keeper:  {file_count} files (cap: 25)  [conditional]

  Custom (from .claude/talisman.yml):       # Only shown if custom Tarnished exist
  - {name} [{prefix}]: {file_count} files (cap: {budget}, source: {source})

Dedup hierarchy: {hierarchy from settings or default}

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
  expected_files: selectedTarnished.map(r => `tmp/reviews/${id}/${r}.md`)
})

// 4. Generate inscription.json (see roundtable-circle/references/inscription-schema.md)
Write("tmp/reviews/{identifier}/inscription.json", { ... })

// 5. Pre-create guard: cleanup stale team if exists (see team-lifecycle-guard.md)
// Validate identifier before rm -rf
if (!/^[a-zA-Z0-9_-]+$/.test(identifier)) throw new Error("Invalid review identifier")
try { TeamDelete() } catch (e) {
  Bash("rm -rf ~/.claude/teams/rune-review-{identifier}/ ~/.claude/tasks/rune-review-{identifier}/ 2>/dev/null")
}
TeamCreate({ team_name: "rune-review-{identifier}" })

// 6. Create tasks (one per Tarnished)
for (const tarnished of selectedTarnished) {
  TaskCreate({
    subject: `Review as ${tarnished}`,
    description: `Files: [...], Output: tmp/reviews/{id}/${tarnished}.md`,
    activeForm: `${tarnished} reviewing...`
  })
}
```

## Phase 3: Spawn Tarnished

Spawn ALL selected Tarnished in a **single message** (parallel execution):

```javascript
// Built-in Tarnished: load prompt from tarnished-prompts/{role}.md
Task({
  team_name: "rune-review-{identifier}",
  name: "{tarnished-name}",
  subagent_type: "general-purpose",
  prompt: /* Load from roundtable-circle/references/tarnished-prompts/{role}.md
             Substitute: {changed_files}, {output_path}, {task_id}, {branch}, {timestamp} */,
  run_in_background: true
})

// Custom Tarnished: use wrapper prompt template from custom-tarnished.md
// The wrapper injects Truthbinding Protocol + Glyph Budget + Seal format
Task({
  team_name: "rune-review-{identifier}",
  name: "{custom.name}",
  subagent_type: "{custom.agent}",  // local name or plugin namespace
  prompt: /* Generate from wrapper template in roundtable-circle/references/custom-tarnished.md
             Substitute: {name}, {file_list}, {output_dir}, {finding_prefix}, {context_budget} */,
  run_in_background: true
})
```

**IMPORTANT**: The Elden Lord MUST NOT review code directly. Focus solely on coordination.

## Phase 4: Monitor

Poll TaskList every 30 seconds until all tasks complete:

```
while (not all tasks completed):
  tasks = TaskList()
  for task in tasks:
    if task.status == "completed": continue
    if task.stale > 5 minutes:
      warn("Tarnished may be stalled")
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
    Deduplicate using hierarchy from settings.dedup_hierarchy (default: SEC > BACK > DOC > QUAL > FRONT).
    Include custom Tarnished outputs in dedup — use their finding_prefix from config.
    Write unified summary to tmp/reviews/{id}/TOME.md.
    See roundtable-circle/references/dedup-runes.md for dedup algorithm.`
})
```

## Phase 6: Verify (Truthsight)

If inscription.json has `verification.enabled: true`:

1. **Layer 0**: Lead runs grep-based inline checks (file paths exist, line numbers valid)
2. **Layer 2**: Spawn Truthsight Verifier for P1 findings (see `rune-orchestration/references/verifier-prompt.md`)
3. Flag any HALLUCINATED findings

## Phase 7: Cleanup & Echo Persist

```javascript
// 1. Shutdown all Tarnished
for (const tarnished of allTarnished) {
  SendMessage({ type: "shutdown_request", recipient: tarnished })
}

// 2. Wait for shutdown approvals (max 30s)

// 3. Cleanup team with fallback (see team-lifecycle-guard.md)
try { TeamDelete() } catch (e) {
  Bash("rm -rf ~/.claude/teams/rune-review-{identifier}/ ~/.claude/tasks/rune-review-{identifier}/ 2>/dev/null")
}

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
| Tarnished timeout (>5 min) | Proceed with partial results |
| Tarnished crash | Report gap in TOME.md |
| ALL Tarnished fail | Abort, notify user |
| Concurrent review running | Warn, offer to cancel previous |
