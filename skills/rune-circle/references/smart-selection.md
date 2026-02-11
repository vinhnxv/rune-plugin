# Smart Selection — Runebearer Scope Assignment

> Assigns files to Runebearers based on extension, priority, and context budget.

## File Classification

### Extension → Runebearer Mapping

| Extension Group | Runebearer | Priority Within Group |
|----------------|-----------|----------------------|
| `*.py, *.go, *.rs, *.rb, *.java, *.kt, *.scala` | Forge Warden | Entry points > services > core modules > utils > tests |
| `*.ts, *.tsx, *.js, *.jsx, *.vue, *.svelte` | Glyph Scribe | Pages/routes > components > hooks > utils |
| `*.md` (>= 10 lines changed) | Lore Keeper | README > CLAUDE.md > docs/ > other .md |
| ALL files | Ward Sentinel | Auth files > API routes > config > infrastructure > other |
| ALL files | Pattern Weaver | Largest files first (highest complexity risk) |

### Skip List (Never Reviewed)

```
*.png, *.jpg, *.gif, *.svg, *.ico, *.woff, *.woff2, *.ttf, *.eot
*.lock, package-lock.json, yarn.lock, bun.lockb, Cargo.lock
*.min.js, *.min.css, *.map
*.pyc, __pycache__/, .git/, node_modules/, dist/, build/, .next/
```

## Three-Way Classification

`select_scope()` returns one of:

| Classification | Meaning | Assigned To |
|---------------|---------|-------------|
| `code` | Source code file | Forge Warden and/or Glyph Scribe + always-on |
| `docs` | Documentation file | Lore Keeper + Ward Sentinel (for `.claude/`) |
| `skip` | Non-reviewable file | No Runebearer |
| `critical_deletion` | Important file deleted | Flagged in TOME.md |

### Dual Classification

Some files are assigned to multiple Runebearers intentionally:

| File Type | Runebearers | Reason |
|-----------|------------|--------|
| `.claude/**/*.md` | Lore Keeper + Ward Sentinel | Docs accuracy + prompt injection risk |
| `Dockerfile` | Ward Sentinel + Forge Warden | Security + build patterns |
| CI/CD configs | Ward Sentinel + Pattern Weaver | Security + convention consistency |
| Test files | Pattern Weaver + Forge Warden | Quality patterns + logic correctness |

## Review Mode Selection

### Review (`/rune:review`)

```
1. Run: git diff --name-only main..HEAD
2. Classify each file by extension
3. Sort by recency: new files first, modified files second
4. Cap per Runebearer by context budget
5. Files beyond budget → "Coverage Gaps" in TOME.md
```

### Audit (`/rune:audit`)

```
1. Run: find . -type f (filtered by skip list)
2. Classify each file by extension
3. Sort by importance: entry points > core > services > utils > tests
4. Cap per Runebearer by context budget (stricter due to volume)
5. Files beyond budget → "Coverage Gaps" in TOME.md
```

### Focus Mode (`--focus <area>`)

| Focus Area | Runebearers Spawned | Budget Increase |
|-----------|-------------------|-----------------|
| `security` | Ward Sentinel only | 2x (40 files) |
| `performance` | Forge Warden only | 2x (60 files) |
| `quality` | Pattern Weaver only | 2x (60 files) |
| `frontend` | Glyph Scribe only | 2x (50 files) |
| `docs` | Lore Keeper only | 2x (50 files) |
| `backend` | Forge Warden + Ward Sentinel | 1.5x each |
| `full` | All (default) | Standard |

Focus mode increases context budget because fewer Runebearers compete for lead attention.

## Context Budget

| Runebearer | Default Budget | Audit Budget | Focus Budget |
|-----------|---------------|-------------|-------------|
| Forge Warden | 30 files | 30 files | 60 files |
| Ward Sentinel | 20 files | 20 files | 40 files |
| Pattern Weaver | 30 files | 30 files | 60 files |
| Glyph Scribe | 25 files | 25 files | 50 files |
| Lore Keeper | 25 files | 25 files | 50 files |

### Budget Enforcement

```
for each selected Runebearer:
  1. Collect files matching extension group
  2. Sort by scope priority (defined above)
  3. Cap at context budget
  4. Remaining files → listed in TOME.md "Coverage Gaps"
```

## Large File Warning

If a single file exceeds 500 lines, it consumes significant context. For files > 500 lines:
- Use `offset`/`limit` to read relevant sections
- Prioritize reading the first 200 lines + any functions flagged by `grep`
- Note in findings if only partial file was reviewed

## References

- [Rune Gaze](rune-gaze.md) — Extension classification rules
- [Circle Registry](circle-registry.md) — Agent-to-Runebearer mapping
