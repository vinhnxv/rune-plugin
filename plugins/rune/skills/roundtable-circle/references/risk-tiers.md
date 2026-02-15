# Risk Tiers — Task Classification

Deterministic risk classification for `/rune:work` tasks. Every task MUST be assigned a tier before execution. Uses a 4-question decision tree with zero ambiguity.

## Tier Summary

| Tier | Name | Risk Level | Example Changes |
|------|------|-----------|-----------------|
| 0 | Grace | Safe | Comments, renames, formatting, tests, docs |
| 1 | Ember | User-visible | API responses, UI components, validation logic |
| 2 | Rune | Infrastructure | DB schemas, CI/CD, migrations, deploy configs |
| 3 | Elden | Irreversible | Auth logic, encryption, credentials, data deletion. Includes: auth, security, encryption, credentials, data deletion |

## Decision Tree

Evaluate questions in order. First YES determines the tier.

```
Q1: Does the task modify auth, security, encryption, or credentials?
    YES --> TIER 3 (Elden)

Q2: Does the task modify DB schemas, migrations, CI/CD, or infrastructure?
    YES --> TIER 2 (Rune)

Q3: Does the task modify user-facing behavior (API, UI, validation, errors)?
    YES --> TIER 1 (Ember)

Q4: Is the task purely internal (rename, comments, formatting, tests, docs)?
    YES --> TIER 0 (Grace)
    NO  --> TIER 1 (Ember) — default to caution
```

## File-Path Fallback Heuristic

When task descriptions are ambiguous, use file paths to determine the default tier:

| Path Pattern | Default Tier |
|-------------|-------------|
| `**/auth/**`, `**/security/**`, `**/crypto/**`, `**/credentials/**` | Tier 3 (Elden) |
| `**/migrations/**`, `**/deploy/**`, `**/.github/**`, `**/infra/**` | Tier 2 (Rune) |
| `**/api/**`, `**/routes/**`, `**/components/**`, `**/views/**` | Tier 1 (Ember) |
| `**/tests/**`, `**/docs/**`, `**/*.md`, `**/__mocks__/**` | Tier 0 (Grace) |

The highest-tier file in a task's scope determines the task's tier. A task touching both `tests/` (Tier 0) and `api/` (Tier 1) is classified as Tier 1.

## Graduated Verification Matrix

| Requirement | Tier 0 | Tier 1 | Tier 2 | Tier 3 |
|-------------|--------|--------|--------|--------|
| Ward check | Basic | Full | Full | Full |
| Self-review | -- | Required | Required | Required |
| Lead review | -- | -- | Required | Required |
| Rollback plan | -- | -- | Required | Required |
| Human confirmation | -- | -- | -- | Required |
| Failure-mode checklist | -- | -- | Required | Required |

## Failure-Mode Checklist (Tier 2+)

Before executing a Tier 2 or Tier 3 task, the worker MUST answer these five questions in the task output:

1. **What breaks if this change is wrong?** (blast radius)
2. **Can the change be reverted with `git revert`?** (rollback viability)
3. **Are there downstream consumers that depend on the current behavior?** (dependency impact)
4. **What is the verification command that proves correctness?** (ward sufficiency)
5. **What is the escalation path if verification fails?** (recovery plan)

If any answer is "unknown" or "unsure", escalate to the Tarnished via `SendMessage` before proceeding.

## TaskCreate Metadata Format

When creating tasks in `/rune:work`, include the risk tier in task metadata:

```
TaskCreate({
  subject: "Update user validation endpoint",
  description: "Modify POST /api/users validation...",
  metadata: {
    risk_tier: 1,
    tier_name: "Ember",
    file_targets: ["src/api/users.ts", "src/validators/user.ts"],
    verification: ["ward check", "self-review"]  // optional — not set by default orchestrator
  }
})
```

## Markdown-Only Projects

For projects consisting entirely of markdown files (like documentation repos or plugin definitions), all tasks will classify as Tier 0 (Grace) via the decision tree. This is correct behavior — markdown changes carry minimal risk. No special handling is needed.

## Cross-References

- Standing Order: SO-4 (Blind Gaze) — triggered when classification is skipped
- Damage Control: DC-2 (Broken Ward) — recovery when tier-required checks fail
- Ward Check: `ward-check.md` — execution details for ward gates
- File Ownership: integrated with risk tiers in `/rune:work` — Tier 2+ tasks should have serialized file ownership
