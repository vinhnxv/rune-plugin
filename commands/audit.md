---
name: audit
description: |
  Full codebase audit using Agent Teams. Spawns up to 5 Runebearer teammates,
  each with their own 200k context window. Scans entire project (or current directory)
  instead of git diff changes. Uses the same 7-phase Rune Circle lifecycle.

  <example>
  user: "/rune:audit"
  assistant: "Starting Rune Circle audit with Agent Teams..."
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

# /rune:audit — Full Codebase Audit

Orchestrate a full codebase audit using the Rune Circle architecture. Each Runebearer gets its own 200k context window via Agent Teams. Unlike `/rune:review` (which reviews only changed files), `/rune:audit` scans the entire project.

**Load skill**: `rune-circle` for full architecture reference.

## Phase 0: Pre-flight

```bash
# Generate audit identifier
audit_id=$(date +%Y%m%d-%H%M%S)

# Scan all project files (excluding non-project directories)
all_files=$(find . -type f \
  ! -path '*/.git/*' \
  ! -path '*/node_modules/*' \
  ! -path '*/__pycache__/*' \
  ! -path '*/tmp/*' \
  ! -path '*/dist/*' \
  ! -path '*/build/*' \
  ! -path '*/.next/*' \
  ! -path '*/.venv/*' \
  ! -path '*/venv/*' \
  ! -path '*/target/*' \
  ! -path '*/.tox/*' \
  ! -path '*/vendor/*' \
  ! -path '*/.cache/*' \
  | sort)

# Optional: get branch name for metadata (not required — audit works without git)
branch=$(git branch --show-current 2>/dev/null || echo "n/a")
```

**Abort conditions:**
- No files found → "No files to audit in current directory."
- Only non-reviewable files (images, lock files, binaries) → "No auditable code found."

**Note:** Unlike `/rune:review`, audit does NOT require a git repository.

## Phase 1: Rune Gaze (Scope Selection)

Classify ALL project files by extension. See `rune-circle/references/rune-gaze.md`.

```
for each file in all_files:
  - *.py, *.go, *.rs, *.rb, *.java, etc. → select Forge Warden
  - *.ts, *.tsx, *.js, *.jsx, etc.       → select Glyph Scribe
  - *.md (>= 10 lines)                   → select Lore Keeper
  - Always: Ward Sentinel (security)
  - Always: Pattern Weaver (quality)
```

Check for project overrides in `.claude/rune-config.yml`.

**Large codebase warning:** If total reviewable files > 150:
```
Note: {count} auditable files found. Each Runebearer's context budget
limits what they can review. Some files may not be fully covered.
```

**Audit file prioritization** (differs from review — prioritize by importance, not recency):
- Forge Warden (max 30): entry points > core modules > utils > tests
- Ward Sentinel (max 20): auth/security files > API routes > infrastructure > other
- Pattern Weaver (max 30): largest files first (highest complexity risk)
- Glyph Scribe (max 25): pages/routes > components > hooks > utils
- Lore Keeper (max 25): README > CLAUDE.md > docs/ > other .md files

## Phase 2: Forge Team

```javascript
// 1. Check for concurrent audit
// If tmp/.rune-audit-{identifier}.json exists and < 30 min old, abort

// 2. Create output directory
Bash("mkdir -p tmp/audit/{audit_id}")

// 3. Write state file
Write("tmp/.rune-audit-{audit_id}.json", {
  team_name: "rune-audit-{audit_id}",
  started: timestamp,
  status: "active",
  audit_scope: ".",
  expected_files: selectedRunebearers.map(r => `tmp/audit/${audit_id}/${r}.md`)
})

// 4. Generate inscription.json (see rune-circle/references/inscription-schema.md)
Write("tmp/audit/{audit_id}/inscription.json", {
  workflow: "rune-audit",
  timestamp: timestamp,
  output_dir: "tmp/audit/{audit_id}/",
  audit_scope: ".",
  teammates: selectedRunebearers.map(r => ({
    name: r,
    output_file: `${r}.md`,
    required_sections: ["P1 (Critical)", "P2 (High)", "P3 (Medium)", "Summary"]
  })),
  verification: { enabled: true }
})

// 5. Create team
TeamCreate({ team_name: "rune-audit-{audit_id}" })

// 6. Create tasks (one per Runebearer)
for (const runebearer of selectedRunebearers) {
  TaskCreate({
    subject: `Audit as ${runebearer}`,
    description: `Files: [...], Output: tmp/audit/${audit_id}/${runebearer}.md`,
    activeForm: `${runebearer} auditing...`
  })
}
```

## Phase 3: Spawn Runebearers

Spawn ALL selected Runebearers in a **single message** (parallel execution):

```javascript
// For each selected Runebearer, spawn as background teammate
Task({
  team_name: "rune-audit-{audit_id}",
  name: "{runebearer-name}",
  subagent_type: "general-purpose",
  prompt: /* Load from rune-circle/references/runebearer-prompts/{role}.md
             Substitute: {changed_files} with audit file list, {output_path}, {task_id}, {branch}, {timestamp} */,
  run_in_background: true
})
```

**IMPORTANT**: The lead MUST NOT audit code itself. Focus solely on coordination.

**Substitution note:** The `{changed_files}` variable in Runebearer prompts is populated with the audit file list (filtered by extension and capped by context budget) rather than git diff output. The Runebearer prompts are designed to work with any file list.

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
  team_name: "rune-audit-{audit_id}",
  name: "runebinder",
  subagent_type: "general-purpose",
  prompt: `Read all findings from tmp/audit/{audit_id}/.
    Deduplicate using hierarchy: SEC > BACK > DOC > QUAL > FRONT.
    Write unified summary to tmp/audit/{audit_id}/TOME.md.
    See rune-circle/references/dedup-runes.md for dedup algorithm.

    TOME header format for audit:
    # TOME — Audit Summary
    **Scope:** {audit_scope}
    **Date:** {timestamp}
    **Runebearers:** {list}
    **Files scanned:** {total_count}
    **Files reviewed:** {reviewed_count} (capped by context budgets)

    Include a "Coverage Gaps" section listing files skipped per Runebearer
    due to context budget caps.`
})
```

## Phase 6: Verify (Truthsight)

If inscription.json has `verification.enabled: true`:

1. **Layer 0**: Lead runs grep-based inline checks (file paths exist, line numbers valid)
2. **Layer 2**: Spawn Truthsight Verifier for P1 findings (see `rune-orchestration/references/verifier-prompt.md`)
3. Flag any HALLUCINATED findings

## Phase 7: Cleanup

```javascript
// 1. Shutdown all Runebearers
for (const runebearer of allRunebearers) {
  SendMessage({ type: "shutdown_request", recipient: runebearer })
}

// 2. Wait for shutdown approvals (max 30s)

// 3. Cleanup team
TeamDelete()

// 4. Read and present TOME.md to user
Read("tmp/audit/{audit_id}/TOME.md")
```

## Error Handling

| Error | Recovery |
|-------|----------|
| Runebearer timeout (>5 min) | Proceed with partial results |
| Runebearer crash | Report gap in TOME.md |
| ALL Runebearers fail | Abort, notify user |
| Concurrent audit running | Warn, offer to cancel previous |
| File count exceeds 150 | Warn about partial coverage, proceed with capped budgets |
| Not a git repo | Works fine — audit uses `find`, not `git diff` |
