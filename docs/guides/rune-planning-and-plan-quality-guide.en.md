# Rune Planning Guide (English): Plan Authoring, Forge, Plan Review, Inspect

This guide covers how to design and validate a high-quality plan before implementation.

Commands covered:
- `/rune:devise`
- `/rune:forge`
- `/rune:plan-review`
- `/rune:inspect`

---

## 1. Planning Command Map

| Command | Primary purpose | Typical output |
|---|---|---|
| `/rune:devise` | Generate a structured implementation plan from a requirement | `plans/YYYY-MM-DD-{type}-{name}-plan.md` |
| `/rune:forge` | Enrich an existing plan with topic-aware specialist input | Same plan file (deepened sections) |
| `/rune:plan-review` | Review plan code samples for correctness/security/pattern issues | `tmp/inspect/{id}/VERDICT.md` |
| `/rune:inspect` | Audit plan vs implementation, or inspect plan itself (`--mode plan`) | `tmp/inspect/{id}/VERDICT.md` |

---

## 2. End-to-End Planning Lifecycle

### Recommended sequence

1. Create baseline plan.
2. Enrich with forge.
3. Review plan quality.
4. Review plan code samples.
5. Freeze plan and execute with arc.

```bash
/rune:devise
/rune:forge plans/2026-02-24-feat-my-feature-plan.md
/rune:plan-review plans/2026-02-24-feat-my-feature-plan.md
/rune:arc plans/2026-02-24-feat-my-feature-plan.md
```

### Fast sequence (time-constrained)

```bash
/rune:devise --quick
/rune:plan-review plans/2026-02-24-feat-my-feature-plan.md
/rune:arc plans/2026-02-24-feat-my-feature-plan.md --no-forge
```

Use this only when requirements are already clear and risks are low.

---

## 3. How to Create a Plan File Correctly

## 3.1 File location and naming

Store plans in `plans/`.
Use the established naming pattern:

```text
plans/YYYY-MM-DD-{type}-{feature-name}-plan.md
```

Example:

```text
plans/2026-02-24-feat-user-auth-plan.md
```

## 3.2 Frontmatter contract

### Core fields (recommended minimum)
- `title`
- `type` (`feat` | `fix` | `refactor`)
- `date`
- `estimated_effort`
- `status`

### Strongly recommended quality fields
- `git_sha`
- `branch`
- `non_goals`
- `tags`
- `affects`

### Example frontmatter template

```yaml
---
title: "feat: Add user authentication with rate limiting"
type: feat
date: 2026-02-24
status: draft
estimated_effort: M
complexity: Medium
risk: Medium
affects:
  - backend/auth/service.py
  - backend/auth/routes.py
  - tests/auth/test_auth_flow.py
tags: [auth, security, rate-limit]
non_goals:
  - "No OAuth providers in this iteration"
git_sha: "a1b2c3d4"
branch: "feat/auth-v1"
session_budget:
  max_concurrent_agents: 5
---
```

## 3.3 Body structure (standard plan)

Recommended sections:
- `# Title`
- `## Overview`
- `## Problem Statement`
- `## Proposed Solution`
- `## Technical Approach`
- `## Acceptance Criteria`
- `## Non-Goals`
- `## Success Criteria`
- `## Dependencies & Risks`
- `## References`

## 3.4 Acceptance criteria format

Use checkbox format. This is important for verification and completion tracking.

~~~markdown
## Acceptance Criteria

- [ ] API endpoint returns expected shape
- [ ] Authentication failures return correct status codes
- [ ] Unit and integration tests cover core and failure paths
~~~

## 3.5 Plan Section Convention (critical)

For sections with pseudocode/code blocks, add contract headers before code:
- `**Inputs**:`
- `**Outputs**:`
- `**Preconditions**:`
- `**Error handling**:`

If pseudocode contains `Bash(...)`, `Error handling` is mandatory.

## 3.6 Common mistakes to avoid

- Missing acceptance criteria checkboxes.
- TODO/FIXME in narrative sections.
- Broken internal heading links.
- Unsafe or invalid file paths.
- Plan references to deleted files not marked/handled.
- Pseudocode without Inputs/Outputs contracts.

---

## 4. `/rune:devise` — Build the Initial Plan

## 4.1 Standard usage

```bash
/rune:devise
```

What it does:
- Brainstorm (default, auto-skippable when requirements are clear)
- Multi-agent research
- Synthesis into plan document
- Optional shatter assessment
- Forge and review phases (unless skipped)

Output pattern:

```text
plans/YYYY-MM-DD-{type}-{feature}-plan.md
```

## 4.2 Common flags

```bash
/rune:devise --quick
/rune:devise --no-forge
/rune:devise --no-brainstorm
/rune:devise --exhaustive
```

When to use:
- `--quick`: time-constrained, clear requirements.
- `--no-forge`: you will run forge manually later.
- `--exhaustive`: high-risk or architecture-heavy features.

---

## 5. `/rune:forge` — Enrich Plan Depth

## 5.1 Standard usage

```bash
/rune:forge plans/2026-02-24-feat-user-auth-plan.md
```

Auto-detect most recent plan:

```bash
/rune:forge
```

Exhaustive enrichment:

```bash
/rune:forge plans/2026-02-24-feat-user-auth-plan.md --exhaustive
```

Skip lore layer if needed:

```bash
/rune:forge plans/2026-02-24-feat-user-auth-plan.md --no-lore
```

## 5.2 Practical notes

- Forge edits the plan file in place (deepens sections).
- Forge does not implement feature code.
- Forge currently has no `--dry-run` mode.

---

## 6. Review the Plan Before Coding

## 6.1 `/rune:plan-review` (recommended)

Use this when your plan contains code samples/pseudocode and you want implementation correctness checks.

```bash
/rune:plan-review plans/2026-02-24-feat-user-auth-plan.md
/rune:plan-review --focus security plans/2026-02-24-feat-user-auth-plan.md
/rune:plan-review --dry-run plans/2026-02-24-feat-user-auth-plan.md
```

`/rune:plan-review` is a thin wrapper around inspect plan mode.

## 6.2 `/rune:inspect --mode plan` (equivalent path)

```bash
/rune:inspect --mode plan plans/2026-02-24-feat-user-auth-plan.md
/rune:inspect --mode plan --focus performance plans/2026-02-24-feat-user-auth-plan.md
```

Use this if you want direct control of inspect flags in one command.

---

## 7. `/rune:inspect` — Validate Implementation Against Plan

After coding starts (or after an arc run), audit plan-vs-implementation completeness:

```bash
/rune:inspect plans/2026-02-24-feat-user-auth-plan.md
/rune:inspect --focus security plans/2026-02-24-feat-user-auth-plan.md
/rune:inspect --fix plans/2026-02-24-feat-user-auth-plan.md
```

Useful flags:
- `--focus <dimension>`
- `--max-agents <1-4>`
- `--threshold <0-100>`
- `--fix`
- `--dry-run`

Result artifact:

```text
tmp/inspect/{id}/VERDICT.md
```

---

## 8. Practical Quality Gate Before `/rune:arc`

Run this sequence before implementation execution:

1. Plan exists and frontmatter is complete.
2. Acceptance criteria are measurable and testable.
3. Pseudocode sections include contracts.
4. Forge enrichment completed (if needed).
5. Plan review completed with major concerns addressed.

Then execute:

```bash
/rune:arc plans/2026-02-24-feat-user-auth-plan.md
```

---

## 9. Greenfield vs Brownfield Planning Tips

### Greenfield
- Prefer broader `devise` + `forge --exhaustive` for design space exploration.
- Keep explicit non-goals to avoid scope explosion.
- Validate architecture assumptions early with plan review.

### Brownfield
- Include concrete affected files in `affects`.
- Be strict on risk and rollback notes in plan sections.
- Use `plan-review --focus security` and `inspect --focus failure-modes` before shipping.

---

## 10. Troubleshooting

| Problem | Likely reason | Action |
|---|---|---|
| Plan review output is weak | Plan lacks clear acceptance criteria/contracts | Rewrite sections with explicit criteria and Inputs/Outputs |
| Forge did not add useful depth | Plan sections too vague | Add clearer section headings and scoped file references |
| Inspect returns broad/generic gaps | Requirements extraction is ambiguous | Rewrite plan requirements as concrete checkable statements |
| Arc later warns on verification gate | Plan quality issues remained | Fix plan, rerun plan-review, then rerun arc |

---

## 11. Minimal Manual Plan Skeleton

~~~markdown
---
title: "feat: <feature>"
type: feat
date: YYYY-MM-DD
status: draft
estimated_effort: M
git_sha: "<short-sha>"
branch: "<branch-name>"
---

# <Feature Title>

## Overview

## Problem Statement

## Proposed Solution

## Technical Approach

### <Sub-problem>
**Inputs**:
**Outputs**:
**Preconditions**:
**Error handling**:

```text
pseudocode here
```

## Acceptance Criteria
- [ ] ...
- [ ] ...

## Non-Goals
- ...

## Success Criteria
- ...

## Dependencies & Risks
- ...

## References
- ...
~~~
