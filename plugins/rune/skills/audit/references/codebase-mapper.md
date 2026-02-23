# Codebase Mapper — File Inventory & Manifest Generation

> Scans the project, collects git metadata, produces `manifest.json`, and computes manifest diffs between runs.

## Overview

The Codebase Mapper runs as Phase 0.1-0.3 of the incremental audit pipeline, between Phase 0 (find) and Phase 0.5 (Lore Layer).

```
Phase 0:   all_files = find(.) → filtered list
Phase 0.1: applyGitignore(all_files) → tracked_files
Phase 0.2: buildManifest(tracked_files) → manifest.json
Phase 0.3: diffManifest(current, previous) → changes
```

## Phase 0.1: Apply Gitignore Filters

```bash
# Use git to resolve .gitignore patterns (respects all nested .gitignore files)
git ls-files --cached --others --exclude-standard 2>/dev/null | sort > /tmp/rune-tracked-files

# For non-git repos: use the raw find output from Phase 0
# Files matching .gitignore patterns are marked status: "excluded"
```

Additional exclusions from talisman config:

```yaml
# talisman.yml
audit:
  incremental:
    extra_skip_patterns:
      - "**/generated/**"
      - "**/*.snapshot.*"
```

## Phase 0.2: Build Manifest

### Batch Git Metadata Extraction

Naive per-file git calls (7 commands x N files) are prohibitively slow. Instead, use 3-4 batch plumbing commands:

```bash
# 1. Current hash for all tracked files (single call)
git ls-files -s
# Output: mode hash stage\tpath

# 2. Last modification per file (single call, parse output)
# Use --since="1 year" ceiling (Concern 2: default, not deferred)
git log --all --format="%H %aI" --name-only --since="1 year"
# Output: hash ISO-date\n\nfile1\nfile2\n\nhash ISO-date\n...

# 3. Contributors + commit count + churn in one 90-day pass
git log --since="90 days ago" --format="%H %aN" --numstat
# Output: hash author\nA\tD\tfile\nA\tD\tfile\n\n...

# 4. Creation date (first commit per file — batchable)
git log --all --diff-filter=A --format="%aI %H" --name-only --since="1 year"
# Output: ISO-date hash\n\nfile1\nfile2\n\n...
```

**Performance**: Reduces 35,000 subprocess forks to 4 git commands for a 5,000-file repo.

### Warm-Run Optimization

Store `last_commit_hash` in manifest. Subsequent runs scan only new commits:

```bash
# Check if we can do a warm run
if [ -n "$last_commit_hash" ]; then
  new_commits=$(git rev-list --count "$last_commit_hash"..HEAD 2>/dev/null)
  if [ "$new_commits" = "0" ]; then
    # No new commits — skip full scan, reuse cached manifest
    return cached_manifest
  fi
  # Incremental scan: only process changed files
  git diff --name-only "$last_commit_hash"..HEAD
fi
```

**Target**: <500ms for 5,000-file repos with no new commits.

### Non-Git Repos

When git is not available:

```bash
# Fallback: use file system metadata
for file in $all_files; do
  size=$(wc -c < "$file")
  lines=$(wc -l < "$file")
  mtime=$(stat -f %m "$file" 2>/dev/null || stat -c %Y "$file" 2>/dev/null)
done
```

No rename detection, no contributor data, no churn metrics. Risk scoring degrades to complexity + role only.

### Manifest Entry Construction

For each file, construct a manifest entry:

```json
{
  "path": "src/auth/service.ts",
  "size_bytes": 4250,
  "line_count": 142,
  "extension": ".ts",
  "category": "backend|frontend|infra|config|doc|test|other",
  "git": {
    "created_at": "ISO8601 or null",
    "modified_at": "ISO8601 or null",
    "current_hash": "abc123 or null",
    "contributors": ["alice", "bob"],
    "contributor_count": 2,
    "commit_count_90d": 12,
    "churn_90d": 340
  },
  "status": "tracked|excluded"
}
```

**Category assignment** uses Rune Gaze extension mapping:
- Backend: `.py`, `.go`, `.rs`, `.rb`, `.java`, `.kt`, `.scala`
- Frontend: `.ts`, `.tsx`, `.js`, `.jsx`, `.vue`, `.svelte`
- Infra: `.sh`, `.bash`, `.tf`, `.sql`, `.dockerfile`
- Config: `.yml`, `.yaml`, `.json`, `.toml`, `.ini`, `.env`
- Doc: `.md`, `.txt`, `.rst`
- Test: files matching `*test*`, `*spec*`, `__test__`
- Other: everything else

### Git History Depth Limit

Use `--since="1 year"` ceiling for creation date detection. For files older than 1 year, fall back to file mtime. This bounds worst-case git scan time.

## Phase 0.3: Diff Manifest

Compare current manifest against previous (stored) manifest:

```
diffManifest(current, previous):
  added = []      # paths in current not in previous
  modified = []   # paths in both but hash differs
  deleted = []    # paths in previous not in current
  renamed = []    # detected via git --diff-filter=R

  for path in current.files:
    if path not in previous.files:
      added.push(path)
    elif current.files[path].git.current_hash != previous.files[path].git.current_hash:
      modified.push(path)

  for path in previous.files:
    if path not in current.files:
      deleted.push(path)

  # Rename detection (only for deleted+added pairs, typically <10 files)
  if added.length > 0 and deleted.length > 0:
    renamed = detectRenames(added, deleted)

  return { added, modified, deleted, renamed }
```

### Rename Detection

Only run on the delta set (deleted+created pairs), not the full codebase:

```bash
# Check candidate pairs from delta
git log --all --diff-filter=R --name-status --since="90 days"
# Output: R100\told-path\tnew-path
```

When a rename is detected:
- Transfer audit history from old path to new path
- Add `previous_paths[]` entry to state record
- Remove old path from state, add new path

### Symlink Handling

Symlinks are excluded from the manifest to prevent infinite recursion and duplicate auditing:

```bash
# Exclude symlinks during Phase 0 find
find . -type f \( ! -type l \) ...
```

## Performance Targets

| Operation | Target | At 5,000 files |
|-----------|--------|----------------|
| Full scan (cold) | <5s | First run |
| Warm scan (cached) | <500ms | No new commits |
| Manifest diff | <1s | 5,000 files |
| Git metadata batch | <3s | 4 git commands |
| Rename detection | <500ms | Only delta pairs |

## Error Handling

| Error | Recovery |
|-------|----------|
| Git not available | Fall back to mtime/ctime, no git metadata |
| Git command fails | Retry once (2s delay), then fall back |
| File permission error | Skip file, mark `status: "error"` |
| Symlink detected | Exclude from manifest |
| Binary file | Include in manifest, mark for skip in audit |
| Encoding error | Skip file metadata, include with defaults |
