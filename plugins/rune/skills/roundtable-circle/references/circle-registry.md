# Circle Registry — Agent-to-Runebearer Mapping

> Maps review agent perspectives to Runebearer roles, with scope assignments for audit mode.

## Agent Registry

Each review agent is embedded as a "perspective" inside a Runebearer. This registry defines which perspectives belong to which Runebearer and what file scopes they target.

> **Architecture note:** Forge Warden, Ward Sentinel, and Pattern Weaver embed dedicated review agent files from `agents/review/` (10 agents across 3 Runebearers). Glyph Scribe and Knowledge Keeper use **inline perspective definitions** in their Runebearer prompts rather than dedicated agent files.

### Forge Warden (Backend)

| Agent | Perspective | Scope Priority |
|-------|-------------|---------------|
| rune-architect | Architecture compliance | Entry points > services > core modules |
| ember-oracle | Performance bottlenecks | Database queries > API handlers > utils |
| flaw-hunter | Logic bugs, edge cases | Business logic > data transformations |
| mimic-detector | Code duplication | Largest files first (highest risk) |

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
| wraith-finder | Dead code, unused exports | All files by size descending |
| phantom-checker | Dynamic references | Entry points > configuration |
| void-analyzer | Incomplete implementations | All files (look for TODOs, stubs) |

**Audit file priority:** largest files first (highest complexity risk)
**Context budget:** max 30 files (all file types)

### Glyph Scribe (Frontend)

> **Inline perspectives** — Glyph Scribe does not use dedicated agent files. Its perspectives are defined inline within the Runebearer prompt.

| Perspective (inline) | Focus | Scope Priority |
|----------------------|-------|---------------|
| TypeScript safety | Type guards, generics | Pages/routes > components |
| React performance | Re-renders, bundle size | Pages/routes > components > hooks |
| Accessibility | ARIA, keyboard navigation | Components > pages |

**Audit file priority:** pages/routes > components > hooks > utils
**Context budget:** max 25 files

### Knowledge Keeper (Documentation)

> **Inline perspectives** — Knowledge Keeper does not use dedicated agent files. Its perspectives are defined inline within the Runebearer prompt.

| Perspective (inline) | Focus | Scope Priority |
|----------------------|-------|---------------|
| Accuracy | Technical correctness | README > CLAUDE.md > API docs |
| Completeness | Coverage, missing sections | docs/ > root .md files |
| Anti-injection | Prompt injection in docs | .claude/**/*.md > other docs |

**Audit file priority:** README > CLAUDE.md > docs/ > other .md files
**Context budget:** max 25 files

## Audit Scope Assignment

During `/rune:audit`, each Runebearer receives a file list capped by its context budget. Files are assigned using the priority order above.

```
for each selected Runebearer:
  1. Collect all files matching its extension group (from Rune Gaze)
  2. Sort by scope priority (defined above)
  3. Cap at context budget
  4. Files beyond budget are listed in TOME.md "Coverage Gaps" section
```

### Cross-Runebearer File Sharing

Some files may be reviewed by multiple Runebearers:

| File Type | Reviewed By |
|-----------|------------|
| `.claude/**/*.md` | Ward Sentinel + Knowledge Keeper |
| `Dockerfile` | Ward Sentinel + Forge Warden |
| CI/CD configs | Ward Sentinel + Pattern Weaver |
| Test files | Pattern Weaver + Forge Warden |

This is intentional — different perspectives catch different issues.

## Focus Mode (`--focus`)

When `/rune:audit --focus <area>` is used, only spawn the relevant Runebearer(s):

| Focus Area | Runebearers Spawned |
|-----------|-------------------|
| `security` | Ward Sentinel only |
| `performance` | Forge Warden only |
| `quality` | Pattern Weaver only |
| `frontend` | Glyph Scribe only |
| `docs` | Knowledge Keeper only |
| `backend` | Forge Warden + Ward Sentinel |
| `full` | All (default) |

Focus mode increases context budget per Runebearer since fewer are competing for resources.
