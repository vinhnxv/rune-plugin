---
name: cleanup
description: |
  Remove tmp/ output directories from completed Rune workflows (reviews, audits, plans, work).
  Preserves Rune Echoes (.claude/echoes/) and active workflow state files.

  <example>
  user: "/rune:cleanup"
  assistant: "Scanning for completed workflow artifacts in tmp/..."
  </example>
user-invocable: true
allowed-tools:
  - Bash
  - Read
  - Glob
---

# /rune:cleanup — Remove Workflow Artifacts

Remove ephemeral `tmp/` output directories from completed Rune workflows. Preserves Rune Echoes and active workflow state.

## What Gets Cleaned

| Directory | Contains | Cleaned? |
|-----------|----------|----------|
| `tmp/reviews/{id}/` | Review outputs, TOME.md, inscription.json | Yes (if completed) |
| `tmp/audit/{id}/` | Audit outputs, TOME.md | Yes (if completed) |
| `tmp/plans/{id}/` | Research findings, plan artifacts | Yes |
| `tmp/work/` | Work agent status files | Yes |
| `tmp/scratch/` | Session scratch pads | Yes |

## What Is Preserved

| Path | Reason |
|------|--------|
| `.claude/echoes/` | Persistent project memory (Rune Echoes) |
| `tmp/.rune-review-*.json` (active) | Active workflow state |
| `tmp/.rune-audit-*.json` (active) | Active workflow state |

## Steps

### 1. Check for Active Workflows

```bash
# Look for active state files (status != completed, cancelled)
ls tmp/.rune-review-*.json tmp/.rune-audit-*.json 2>/dev/null
```

For each state file found, read and check status:
- `"status": "running"` or `"status": "spawning"` → **SKIP** associated directory, warn user
- `"status": "completed"` or `"status": "cancelled"` → Safe to clean

### 2. Inventory Artifacts

```bash
# List all tmp/ directories with sizes
du -sh tmp/reviews/*/  tmp/audit/*/  tmp/plans/*/  tmp/work/  tmp/scratch/ 2>/dev/null
```

### 3. Confirm with User

Display summary:

```
Cleanup Summary:
  Reviews:  3 directories (2.1 MB)
  Audits:   1 directory  (800 KB)
  Plans:    2 directories (400 KB)
  Scratch:  1 directory  (50 KB)
  Total:    ~3.4 MB

Active workflows (PRESERVED):
  - tmp/.rune-review-142.json (running)

Proceed? [Y/n]
```

### 4. Remove Artifacts

```bash
# Remove completed review directories
rm -rf tmp/reviews/{completed_ids}/

# Remove completed audit directories
rm -rf tmp/audit/{completed_ids}/

# Remove plan research artifacts
rm -rf tmp/plans/

# Remove work status files
rm -rf tmp/work/

# Remove scratch files
rm -rf tmp/scratch/

# Remove completed state files
rm tmp/.rune-review-{completed_ids}.json
rm tmp/.rune-audit-{completed_ids}.json
```

### 5. Report

```
Cleanup complete.
  Removed: 7 directories, ~3.4 MB freed
  Preserved: 1 active workflow (review #142)

Rune Echoes (.claude/echoes/) untouched.
```

## Flags

| Flag | Effect |
|------|--------|
| `--all` | Remove ALL tmp/ artifacts (skip active check) |
| `--dry-run` | Show what would be removed without deleting |

### --dry-run Example

```
[DRY RUN] Would remove:
  tmp/reviews/142/  (7 files, 1.2 MB)
  tmp/reviews/155/  (5 files, 900 KB)
  tmp/audit/20260211-103000/  (8 files, 800 KB)
  tmp/.rune-review-142.json  (completed)
  tmp/.rune-review-155.json  (completed)
  tmp/.rune-audit-20260211-103000.json  (cancelled)

Would preserve:
  .claude/echoes/  (persistent memory)
```

## Notes

- This command is safe to run at any time — active workflows are detected and preserved
- Rune Echoes are NEVER touched by cleanup (they live in `.claude/echoes/`, not `tmp/`)
- Completed/cancelled state files are removed along with their output directories
- If `tmp/` directory doesn't exist, reports "Nothing to clean"
