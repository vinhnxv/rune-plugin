# Entry Examples

Example echo entries for all 5 tiers showing full metadata format and content patterns.

**Inputs**: None (reference documentation)
**Outputs**: None (reference documentation)
**Preconditions**: Understanding of the 5-tier lifecycle (Etched/Notes/Inscribed/Observations/Traced)

## Etched (permanent)

```markdown
### [2026-02-11] Architecture: Express + Prisma async
- **layer**: etched
- **source**: manual
- **confidence**: 1.0
- **evidence**: `package.json:5-15` — framework dependencies
- **verified**: 2026-02-11
- **supersedes**: none
- Backend uses Express with Prisma ORM. All repository methods are async.
  Domain layer has no framework imports. DI container manages dependencies.
```

## Notes (user-explicit)

```markdown
## Notes — Always use bun instead of npm (2026-02-11)
**Source**: user:remember
- User-explicit memory. Always use bun for package management in this project.
  Never suggest npm install or npm run — use bun install and bun run instead.
```

## Inscribed (tactical)

```markdown
### [2026-02-11] Pattern: Unused imports in new files
- **layer**: inscribed
- **source**: rune:appraise PR #42
- **confidence**: 0.85
- **evidence**: `src/auth.py:1-5` — 3 unused imports found
- **verified**: 2026-02-11
- **supersedes**: none
- Codebase tends to leave unused imports in newly created files.
  Reviewers should flag import hygiene in new files specifically.
```

## Observations (agent-observed)

```markdown
## Observations — Service layer tends to miss error handling (2026-02-11)
**Source**: rune:appraise PR #45
- Agent-observed pattern. Service layer methods often lack try/catch for
  external API calls. Seen in 3 recent reviews. Will auto-promote to
  Inscribed after 3 search references.
```

## Traced (session)

```markdown
### [2026-02-11] Observation: Slow test suite in CI
- **layer**: traced
- **source**: rune:strive session-abc
- **confidence**: 0.6
- **evidence**: CI logs — test suite took 8min (vs 3min baseline)
- **verified**: 2026-02-11
- **supersedes**: none
- Test suite is unusually slow today, possibly due to new integration tests.
```
