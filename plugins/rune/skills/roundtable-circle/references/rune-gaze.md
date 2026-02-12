# Rune Gaze — Scope Selection

> Extension-based file classification for Tarnished selection. Generic and configurable.

## Table of Contents

- [File Classification Algorithm](#file-classification-algorithm)
- [Extension Groups](#extension-groups)
  - [Backend Extensions](#backend-extensions)
  - [Frontend Extensions](#frontend-extensions)
  - [Documentation Extensions](#documentation-extensions)
  - [Skip Extensions (Never Review)](#skip-extensions-never-review)
- [Tarnished Selection Matrix](#tarnished-selection-matrix)
- [Configurable Overrides](#configurable-overrides)
- [Special File Handling](#special-file-handling)
  - [Critical Files (Always Review)](#critical-files-always-review)
  - [Critical Deletions](#critical-deletions)
- [Line Count Threshold for Docs](#line-count-threshold-for-docs)

## File Classification Algorithm

```
Input: list of changed files (from git diff)
Output: { code_files, doc_files, skip_files, tarnished_selections }

for each file in changed_files:
  ext = file.extension

  if ext in SKIP_EXTENSIONS:
    skip_files.add(file)
    continue

  if ext in BACKEND_EXTENSIONS:
    code_files.add(file)
    tarnished_selections.add("forge-warden")

  if ext in FRONTEND_EXTENSIONS:
    code_files.add(file)
    tarnished_selections.add("glyph-scribe")

  if ext in DOC_EXTENSIONS:
    if lines_changed(file) >= 10:
      doc_files.add(file)
      tarnished_selections.add("knowledge-keeper")
    else:
      skip_files.add(file)  # Minor doc change

# Always-on Tarnished (regardless of file types)
tarnished_selections.add("ward-sentinel")   # Security: always
tarnished_selections.add("pattern-weaver")  # Quality: always
```

## Extension Groups

### Backend Extensions

```
.py, .go, .rs, .rb, .java, .kt, .scala, .cs, .php, .ex, .exs, .erl, .hs, .ml
```

### Frontend Extensions

```
.ts, .tsx, .js, .jsx, .vue, .svelte, .astro
```

### Documentation Extensions

```
.md, .mdx, .rst, .txt, .adoc
```

### Skip Extensions (Never Review)

```
# Binary / generated
.png, .jpg, .jpeg, .gif, .svg, .ico, .woff, .woff2, .ttf, .eot
.pdf, .zip, .tar, .gz

# Lock files
package-lock.json, yarn.lock, bun.lockb, Cargo.lock, poetry.lock, uv.lock
Gemfile.lock, pnpm-lock.yaml, go.sum, composer.lock

# Build output
.min.js, .min.css, .map, .d.ts (from generated)

# Config (usually boilerplate)
.gitignore, .editorconfig, .prettierrc, .eslintrc
```

## Tarnished Selection Matrix

| Changed Files | Forge Warden | Ward Sentinel | Pattern Weaver | Glyph Scribe | Knowledge Keeper |
|--------------|:------------:|:-------------:|:--------------:|:------------:|:-----------:|
| Only backend | Selected | **Always** | **Always** | - | - |
| Only frontend | - | **Always** | **Always** | Selected | - |
| Only docs (>= 10 lines) | - | **Always** | **Always** | - | Selected |
| Backend + frontend | Selected | **Always** | **Always** | Selected | - |
| Backend + docs | Selected | **Always** | **Always** | - | Selected |
| All types | Selected | **Always** | **Always** | Selected | Selected |

**Max built-in Tarnished:** 5. With custom Tarnished (via `rune-config.yml`), total can reach 8 (`settings.max_tarnished`). Plus 1 Runebinder (utility) for aggregation.

## Configurable Overrides

Projects can override the default extension groups via `.claude/rune-config.yml`:

```yaml
# .claude/rune-config.yml (optional)
rune-gaze:
  backend_extensions:
    - .py
    - .go
  frontend_extensions:
    - .tsx
    - .ts
  skip_patterns:
    - "**/*.generated.ts"
    - "**/migrations/**"
  always_review:
    - "CLAUDE.md"
    - ".claude/**/*.md"
```

If no config file exists, use the defaults above.

## Special File Handling

### Critical Files (Always Review)

Some files should always be reviewed regardless of extension:
- `CLAUDE.md` — Agent instructions (security-sensitive)
- `.claude/**/*.md` — Agent/skill definitions (security-sensitive)
- `Dockerfile`, `docker-compose.yml` — Infrastructure
- CI/CD configs (`.github/workflows/`, `.gitlab-ci.yml`)

These get dual classification: normal type + security (Ward Sentinel always sees them).

### Critical Deletions

Files that were deleted should be flagged:
- Deletion of test files → Pattern Weaver alert
- Deletion of security configs → Ward Sentinel alert
- Deletion of any `.claude/` file → Ward Sentinel + Pattern Weaver alert

## Line Count Threshold for Docs

The `>= 10 lines changed` threshold for Knowledge Keeper prevents spawning a full doc reviewer for trivial edits (typo fixes, whitespace).

Calculate with:
```bash
git diff --stat main..HEAD -- "*.md" | grep -E "\d+ insertion|\d+ deletion"
```
