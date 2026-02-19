# Circle Registry — Agent-to-Ash Mapping

> Maps review agent perspectives to Ash roles, with scope assignments for audit mode.

## Agent Registry

Each review agent is embedded as a "perspective" inside an Ash. This registry defines which perspectives belong to which Ash and what file scopes they target.

> **Architecture note:** Forge Warden, Ward Sentinel, and Pattern Weaver embed dedicated review agent files from `agents/review/` (18 agents across 3 Ashes). Glyph Scribe, Knowledge Keeper, and Codex Oracle use **inline perspective definitions** in their Ash prompts rather than dedicated agent files.

### Forge Warden (Backend)

| Agent | Perspective | Scope Priority |
|-------|-------------|---------------|
| rune-architect | Architecture compliance | Entry points > services > core modules |
| ember-oracle | Performance bottlenecks | Database queries > API handlers > utils |
| flaw-hunter | Logic bugs, edge cases | Business logic > data transformations |
| mimic-detector | Code duplication | Largest files first (highest risk) |
| type-warden | Type safety, language idioms | All backend source files |
| depth-seer | Missing logic, complexity | Services > handlers > core modules |
| blight-seer | Design anti-patterns, architectural smells | Entry points > services > core modules |
| forge-keeper | Data integrity, migration safety, lock analysis | Migration files > model files > transaction code |

**Audit file priority:** entry points > core modules > services > utils > tests
**Context budget:** max 30 files

### Ward Sentinel (Security)

| Agent | Perspective | Scope Priority |
|-------|-------------|---------------|
| ward-sentinel | Vulnerabilities, OWASP | Auth files > API routes > infrastructure |

**Audit file priority:** auth/security > API routes > configuration > infrastructure > other
**Context budget:** max 20 files (all file types)

### Pattern Weaver (Quality)

| Agent | Perspective | Scope Priority |
|-------|-------------|---------------|
| simplicity-warden | YAGNI, over-engineering | Largest/most complex files first |
| pattern-seer | Naming, conventions | All files by size descending |
| wraith-finder | Dead code, unwired code, DI wiring, orphaned routes/handlers | All files by size descending |
| phantom-checker | Dynamic references | Entry points > configuration |
| void-analyzer | Incomplete implementations | All files (look for TODOs, stubs) |
| trial-oracle | TDD compliance, test quality | Test files > source files |
| tide-watcher | Async/concurrency patterns, race conditions | Async code > event handlers > frontend |
| refactor-guardian | Refactoring completeness, orphaned callers, extraction verification | Changed files with R/D/A git status |
| reference-validator | Import paths, config refs, frontmatter, version sync | All changed files + config files |

**Audit file priority:** largest files first (highest complexity risk)
**Context budget:** max 30 files (all file types)

### Glyph Scribe (Frontend)

> **Inline perspectives** — Glyph Scribe does not use dedicated agent files. Its perspectives are defined inline within the Ash prompt.

| Perspective (inline) | Focus | Scope Priority |
|----------------------|-------|---------------|
| TypeScript safety | Type guards, generics | Pages/routes > components |
| React performance | Re-renders, bundle size | Pages/routes > components > hooks |
| Accessibility | ARIA, keyboard navigation | Components > pages |

**Audit file priority:** pages/routes > components > hooks > utils
**Context budget:** max 25 files

### Knowledge Keeper (Documentation)

> **Inline perspectives** — Knowledge Keeper does not use dedicated agent files. Its perspectives are defined inline within the Ash prompt.

| Perspective (inline) | Focus | Scope Priority |
|----------------------|-------|---------------|
| Accuracy | Technical correctness | README > CLAUDE.md > API docs |
| Completeness | Coverage, missing sections | docs/ > root .md files |
| Consistency | Cross-reference accuracy | All docs cross-checked |
| Readability | Clear, scannable documentation | All .md files |
| Security | Prompt injection in docs | .claude/**/*.md > other docs |

**Audit file priority:** README > CLAUDE.md > docs/ > other .md files
**Context budget:** max 25 files

### Codex Oracle (Cross-Model)

> **External CLI** — Codex Oracle invokes `codex exec` via Bash, unlike other Ashes which use Claude Code tools directly. Auto-detected, conditionally summoned. Uses **inline perspective definitions** (like Glyph Scribe and Knowledge Keeper).

| Perspective (inline) | Focus | Scope Priority |
|----------------------|-------|---------------|
| Cross-model security | Issues that Claude Ashes might miss | Auth files > API routes > infrastructure |
| Cross-model logic | Edge cases, concurrency, error handling | Business logic > data transformations |
| Cross-model quality | Duplication, API design, validation gaps | All file types |

**Activation:** `command -v codex` returns 0 AND `talisman.codex.disabled` is not true
**Audit file priority:** new files > modified files > high-risk files > other
**Context budget:** max 20 files (configurable via talisman)
**Finding prefix:** `CDX`

## Audit Scope Assignment

During `/rune:audit`, each Ash receives a file list capped by its context budget. Files are assigned using the priority order above.

```
for each selected Ash:
  1. Collect all files matching its extension group (from Rune Gaze)
  2. Sort by scope priority (defined above)
  3. Cap at context budget
  4. Files beyond budget are listed in TOME.md "Coverage Gaps" section
```

### Cross-Ash File Sharing

Some files may be reviewed by multiple Ash:

| File Type | Reviewed By |
|-----------|------------|
| `.claude/**/*.md` | Ward Sentinel + Knowledge Keeper |
| `Dockerfile` | Ward Sentinel + Forge Warden |
| CI/CD configs | Ward Sentinel + Pattern Weaver |
| Test files | Pattern Weaver + Forge Warden |
| ALL files (when codex available) | Codex Oracle (cross-model perspective) |

This is intentional — different perspectives catch different issues.

## Focus Mode (`--focus`)

When `/rune:audit --focus <area>` is used, only summon the relevant Ash(s):

| Focus Area | Ash Summoned |
|-----------|-------------------|
| `security` | Ward Sentinel only |
| `performance` | Forge Warden only |
| `quality` | Pattern Weaver only |
| `frontend` | Glyph Scribe only |
| `docs` | Knowledge Keeper only |
| `backend` | Forge Warden + Ward Sentinel |
| `cross-model` | Codex Oracle only |
| `full` | All (default) |

Focus mode increases context budget per Ash since fewer are competing for resources.
