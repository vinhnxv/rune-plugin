---
name: rune:review
description: |
  Multi-agent code review using Agent Teams. Summons up to 5 built-in Ashes
  (plus custom Ash from talisman.yml), each with their own 200k context window.
  Handles scope selection, team creation, review orchestration, aggregation, verification, and cleanup.

  <example>
  user: "/rune:review"
  assistant: "The Tarnished convenes the Roundtable Circle for review..."
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

Orchestrate a multi-agent code review using the Roundtable Circle architecture. Each Ash gets its own 200k context window via Agent Teams.

**Load skills**: `roundtable-circle`, `context-weaving`, `rune-echoes`, `rune-orchestration`

## Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--partial` | Review only staged files (`git diff --cached`) instead of full branch diff | Off (reviews all branch changes) |
| `--dry-run` | Show scope selection and Ash plan without summoning agents | Off |
| `--max-agents <N>` | Limit total Ash summoned (built-in + custom). Range: 1-8 | All selected |

**Partial mode** is useful for reviewing a subset of changes before committing, rather than the full branch diff against the default branch.

**Dry-run mode** executes Phase 0 (Pre-flight) and Phase 1 (Rune Gaze) only, then displays:
- Changed files classified by type
- Which Ash would be summoned
- File assignments per Ash (with context budget caps)
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
- All doc-extension files fell below line threshold AND code files exist → summon only always-on Ashes (normal behavior — minor doc changes alongside code are noise)

**Docs-only override:** If ALL non-skip files are doc-extension and ALL fall below the line threshold (no code files at all), promote them so Knowledge Keeper is still summoned. This prevents a degenerate case where a docs-only diff silently skips all files. See `rune-gaze.md` for the full algorithm.

### Load Custom Ashes

After collecting changed files, check for custom Ash config:

```
1. Read .claude/talisman.yml (project) or ~/.claude/talisman.yml (global)
2. If ashes.custom[] exists:
   a. Validate: unique prefixes, unique names, resolvable agents, count ≤ max
   b. Filter by workflows: keep only entries with "review" in workflows[]
   c. Match triggers against changed_files (extension + path match)
   d. Skip entries with fewer matching files than trigger.min_files
3. Merge validated custom Ash with built-in selections
4. Apply defaults.disable_ashes to remove any disabled built-ins
```

See `roundtable-circle/references/custom-ashes.md` for full schema and validation rules.

## Phase 1: Rune Gaze (Scope Selection)

Classify changed files by extension. See `roundtable-circle/references/rune-gaze.md`.

```
for each file in changed_files:
  - *.py, *.go, *.rs, *.rb, *.java, etc.           → select Forge Warden
  - *.ts, *.tsx, *.js, *.jsx, etc.                  → select Glyph Scribe
  - Dockerfile, *.sh, *.sql, *.tf, CI/CD configs    → select Forge Warden (infra)
  - *.yml, *.yaml, *.json, *.toml, *.ini            → select Forge Warden (config)
  - *.md (>= 10 lines changed)                      → select Knowledge Keeper
  - .claude/**/*.md                                  → select Knowledge Keeper + Ward Sentinel (security boundary)
  - Unclassified (not in any group or skip list)     → select Forge Warden (catch-all)
  - Always: Ward Sentinel (security)
  - Always: Pattern Weaver (quality)

# Custom Ashes (from talisman.yml):
for each custom in validated_custom_ash:
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

Ash to summon: {count} ({built_in_count} built-in + {custom_count} custom)
  Built-in:
  - Forge Warden:      {file_count} files (cap: 30)
  - Ward Sentinel:     {file_count} files (cap: 20)
  - Pattern Weaver:    {file_count} files (cap: 30)
  - Glyph Scribe:      {file_count} files (cap: 25)  [conditional]
  - Knowledge Keeper:  {file_count} files (cap: 25)  [conditional]

  Custom (from .claude/talisman.yml):       # Only shown if custom Ash exist
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
  expected_files: selectedAsh.map(r => `tmp/reviews/${identifier}/${r}.md`)
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

// 6. Create tasks (one per Ash)
for (const ash of selectedAsh) {
  TaskCreate({
    subject: `Review as ${ash}`,
    description: `Files: [...], Output: tmp/reviews/{identifier}/${ash}.md`,
    activeForm: `${ash} reviewing...`
  })
}
```

## Phase 3: Summon Ash

Summon ALL selected Ash in a **single message** (parallel execution):

```javascript
// Built-in Ash: load prompt from ash-prompts/{role}.md
Task({
  team_name: "rune-review-{identifier}",
  name: "{ash-name}",
  subagent_type: "general-purpose",
  prompt: /* Load from roundtable-circle/references/ash-prompts/{role}.md
             Substitute: {changed_files}, {output_path}, {task_id}, {branch}, {timestamp} */,
  run_in_background: true
})

// Custom Ash: use wrapper prompt template from custom-ashes.md
// The wrapper injects Truthbinding Protocol + Glyph Budget + Seal format
Task({
  team_name: "rune-review-{identifier}",
  name: "{custom.name}",
  subagent_type: "{custom.agent}",  // local name or plugin namespace
  prompt: /* Generate from wrapper template in roundtable-circle/references/custom-ashes.md
             Substitute: {name}, {file_list}, {output_dir}, {finding_prefix}, {context_budget} */,
  run_in_background: true
})
```

**IMPORTANT**: The Tarnished MUST NOT review code directly. Focus solely on coordination.

## Phase 4: Monitor

Poll TaskList every 30 seconds until all tasks complete:

```
while (not all tasks completed):
  tasks = TaskList()
  for task in tasks:
    if task.status == "completed": continue
    if task.stale > 5 minutes:
      warn("Ash may be stalled")
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
  prompt: `Read all findings from tmp/reviews/{identifier}/.
    Deduplicate using hierarchy from settings.dedup_hierarchy (default: SEC > BACK > DOC > QUAL > FRONT).
    Include custom Ash outputs in dedup — use their finding_prefix from config.
    Write unified summary to tmp/reviews/{identifier}/TOME.md.
    See roundtable-circle/references/dedup-runes.md for dedup algorithm.`
})
```

## Phase 6: Verify (Truthsight)

If inscription.json has `verification.enabled: true`:

1. **Layer 0**: Lead runs grep-based inline checks (file paths exist, line numbers valid)
2. **Layer 2**: Summon Truthsight Verifier for P1 findings (see `rune-orchestration/references/verifier-prompt.md`)
3. Flag any HALLUCINATED findings

## Phase 7: Cleanup & Echo Persist

```javascript
// 1. Shutdown all Ash
for (const ash of allAsh) {
  SendMessage({ type: "shutdown_request", recipient: ash })
}

// 2. Wait for shutdown approvals (max 30s)

// 3. Cleanup team with fallback (see team-lifecycle-guard.md)
try { TeamDelete() } catch (e) {
  Bash("rm -rf ~/.claude/teams/rune-review-{identifier}/ ~/.claude/tasks/rune-review-{identifier}/ 2>/dev/null")
}

// 4. Update state file to completed
Write("tmp/.rune-review-{identifier}.json", {
  team_name: "rune-review-{identifier}",
  started: timestamp,
  status: "completed",
  completed: new Date().toISOString(),
  expected_files: selectedAsh.map(r => `tmp/reviews/${identifier}/${r}.md`)
})

// 5. Persist learnings to Rune Echoes (if .claude/echoes/ exists)
//    Extract P1/P2 patterns from TOME.md and write as Inscribed entries
//    See rune-echoes skill for entry format and write protocol
if (exists(".claude/echoes/reviewer/")) {
  patterns = extractRecurringPatterns("tmp/reviews/{identifier}/TOME.md")
  for (const pattern of patterns) {
    appendEchoEntry(".claude/echoes/reviewer/MEMORY.md", {
      layer: "inscribed",
      source: `rune:review ${identifier}`,
      confidence: pattern.confidence,
      evidence: pattern.evidence,
      content: pattern.summary
    })
  }
}

// 6. Read and present TOME.md to user
Read("tmp/reviews/{identifier}/TOME.md")
```

## Error Handling

| Error | Recovery |
|-------|----------|
| Ash timeout (>5 min) | Proceed with partial results |
| Ash crash | Report gap in TOME.md |
| ALL Ash fail | Abort, notify user |
| Concurrent review running | Warn, offer to cancel previous |
