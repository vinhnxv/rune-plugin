---
name: rune:rest
description: |
  Remove tmp/ output directories from completed Rune workflows (reviews, audits, plans, work, mend, arc).
  Preserves Rune Echoes (.claude/echoes/) and active workflow state files.
  Renamed from /rune:cleanup in v1.5.0 — "rest" as in a resting place for completed artifacts.

  <example>
  user: "/rune:rest"
  assistant: "Scanning for completed workflow artifacts in tmp/..."
  </example>
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - AskUserQuestion
---

# /rune:rest — Remove Workflow Artifacts

Remove ephemeral `tmp/` output directories from completed Rune workflows. Preserves Rune Echoes and active workflow state.

## What Gets Cleaned

| Directory | Contains | Cleaned? |
|-----------|----------|----------|
| `tmp/reviews/{id}/` | Review outputs, TOME.md, inscription.json | Yes (if completed) |
| `tmp/audit/{id}/` | Audit outputs, TOME.md | Yes (if completed) |
| `tmp/plans/{id}/` | Research findings, plan artifacts | Yes |
| `tmp/work/` | Work agent status files | Yes |
| `tmp/scratch/` | Session scratch pads | Yes |
| `tmp/mend/{id}/` | Mend resolution reports, fixer outputs | Yes (if completed) |
| `tmp/arc/{id}/` | Arc pipeline artifacts (enriched plans, TOME, reports) | Yes (if completed) |

## What Is Preserved

| Path | Reason |
|------|--------|
| `.claude/echoes/` | Persistent project memory (Rune Echoes) |
| `.claude/arc/{id}/checkpoint.json` | Arc resume state (needed for --resume) |
| `tmp/.rune-review-*.json` (active) | Active workflow state |
| `tmp/.rune-audit-*.json` (active) | Active workflow state |
| `tmp/.rune-mend-*.json` (active) | Mend concurrency detection |

## Steps

### 1. Check for Active Workflows

```bash
# Look for active state files (status != completed, cancelled)
ls tmp/.rune-review-*.json tmp/.rune-audit-*.json tmp/.rune-mend-*.json 2>/dev/null
```

For each state file found, read and check status:
- `"status": "active"` → **SKIP** associated directory, warn user
- `"status": "completed"` or `"status": "cancelled"` → Safe to clean

### 2. Inventory Artifacts

```bash
# List all tmp/ directories with sizes
du -sh tmp/reviews/*/  tmp/audit/*/  tmp/plans/*/  tmp/work/  tmp/scratch/  tmp/mend/*/  tmp/arc/*/ 2>/dev/null
```

### 3. Confirm with User

Display summary:

```
Cleanup Summary:
  Reviews:  3 directories (2.1 MB)
  Audits:   1 directory  (800 KB)
  Plans:    2 directories (400 KB)
  Mend:     1 directory  (200 KB)
  Arc:      1 directory  (1.5 MB)
  Scratch:  1 directory  (50 KB)
  Total:    ~5.1 MB

Active workflows (PRESERVED):
  - tmp/.rune-review-142.json (active)
  - .claude/arc/abc123/checkpoint.json (arc resume state)

Proceed? [Y/n]
```

### 4. Validate Paths

Before removing any directory, verify paths are within `tmp/`:

```bash
# Validate each path resolves inside tmp/ (prevents traversal and symlink attacks)
for dir in "${dirs_to_remove[@]}"; do
  # Reject symlinks — do not follow them
  if [[ -L "$dir" ]]; then
    echo "SKIP: $dir is a symlink (not following)"
    continue
  fi
  resolved=$(realpath -s "$dir" 2>/dev/null || (cd "$dir" 2>/dev/null && pwd))
  if [[ "$resolved" != "$(realpath -s tmp 2>/dev/null || (cd tmp && pwd))"/* ]]; then
    echo "SKIP: $dir resolves outside tmp/ ($resolved)"
    continue
  fi
done
```

Any path that resolves outside `tmp/` or is a symlink is skipped with a warning. This prevents accidental deletion from symlinks or malformed state file entries.

### 5. Remove Artifacts

```bash
# Remove completed review directories (validated paths only)
rm -rf tmp/reviews/{completed_ids}/

# Remove completed audit directories (validated paths only)
rm -rf tmp/audit/{completed_ids}/

# Remove completed mend directories (validated paths only)
rm -rf tmp/mend/{completed_ids}/

# Remove completed arc directories (validated paths only)
rm -rf tmp/arc/{completed_ids}/

# Remove plan research artifacts
rm -rf tmp/plans/

# Remove work status files
rm -rf tmp/work/

# Remove scratch files
rm -rf tmp/scratch/

# Remove completed state files
rm tmp/.rune-review-{completed_ids}.json
rm tmp/.rune-audit-{completed_ids}.json
rm tmp/.rune-mend-{completed_ids}.json
```

**Note:** `tmp/plans/`, `tmp/work/`, and `tmp/scratch/` are removed unconditionally (no active-state check). These directories do not have state files and are always safe to clean. `tmp/mend/` and `tmp/arc/` directories follow the same active-state check as reviews and audits. Arc checkpoint state at `.claude/arc/` is NEVER cleaned — it lives outside `tmp/` and is needed for `--resume`.

### 6. Report

```
Cleanup complete.
  Removed: 7 directories, ~3.4 MB freed
  Preserved: 1 active workflow (review #142)

Rune Echoes (.claude/echoes/) untouched.
```

## Flags

| Flag | Effect |
|------|--------|
| `--all` | Remove ALL tmp/ artifacts including active workflows. Still requires user confirmation (Step 3). |
| `--dry-run` | Show what would be removed without deleting. Combinable with `--all` to preview full cleanup scope. |

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

## Error Handling

| Error | Recovery |
|-------|----------|
| `tmp/` doesn't exist | Report "Nothing to clean" |
| State file unreadable (corrupt JSON) | Treat associated directory as active (skip) |
| Path resolves outside `tmp/` | Skip with warning, do not delete |
| Permission denied on remove | Report which directories failed, continue with rest |

## Notes

- This command is safe to run at any time — active workflows are detected and preserved
- Rune Echoes are NEVER touched by cleanup (they live in `.claude/echoes/`, not `tmp/`)
- Completed/cancelled state files are removed along with their output directories
- If `tmp/` directory doesn't exist, reports "Nothing to clean"
