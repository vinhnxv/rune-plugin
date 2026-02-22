# Todo Template — Source-Aware

This template adapts based on the `source` field. Sections marked with source conditions should be included only when the source matches.

## YAML Frontmatter

```yaml
---
schema_version: 1
status: pending
priority: p2
issue_id: "XXX"
source: review
source_ref: ""
finding_id: ""
finding_severity: ""
tags: []
dependencies: []
files: []
assigned_to: null
work_session: ""
created: "YYYY-MM-DD"
updated: "YYYY-MM-DD"
---
```

### Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | integer | Yes | Always `1` for current schema |
| `status` | string | Yes | `pending`, `ready`, `in_progress`, `complete`, `blocked`, `wont_fix` |
| `priority` | string | Yes | `p1` (critical), `p2` (important), `p3` (nice-to-have) |
| `issue_id` | string | Yes | 3-digit padded sequential ID |
| `source` | string | Yes | `review`, `work`, `pr-comment`, `tech-debt`, `audit` |
| `source_ref` | string | No | Path or reference to origin (e.g., TOME path, plan path) |
| `finding_id` | string | No | RUNE:FINDING id for review/audit sources |
| `finding_severity` | string | No | Original severity from TOME (P1/P2/P3) |
| `tags` | list | No | Categorization tags |
| `dependencies` | list | No | Issue IDs this todo is blocked by |
| `files` | list | No | Affected file paths |
| `assigned_to` | string | No | Worker or agent assigned to this todo |
| `work_session` | string | No | Session ID for stale detection |
| `created` | string | Yes | ISO date of creation |
| `updated` | string | Yes | ISO date of last update |

## Template Body

```markdown
# {Brief Task Title}

## Problem Statement

What is broken, missing, or needs improvement?

## Findings

{Source-conditional sections — include only the matching source block}
```

### Source: review / audit

Include when `source` is `review` or `audit`. Auto-populated from TOME findings.

```markdown
## Findings

- **Finding ID**: {finding_id}
- **File**: `{file}:{line}`
- **Rune Trace**:
  ```
  {code snippet from TOME finding}
  ```
- **Issue**: {description from TOME}
- **Severity**: {finding_severity}
- **Scope**: {diff-scope attribute if available}
```

### Source: work

Include when `source` is `work`. Auto-populated from plan tasks.

```markdown
## Findings

- **Plan task**: {task subject}
- **Plan ref**: `{source_ref}`
- **Risk tier**: {risk tier from plan metadata}
- **Description**: {task description from plan}
```

### Source: pr-comment

Include when `source` is `pr-comment`. Auto-populated from GitHub PR comments.

```markdown
## Findings

- **PR**: #{pr-number}
- **Comment**: {comment body}
- **File**: `{file}:{line}`
- **Author**: {comment author}
```

### Source: tech-debt

Include when `source` is `tech-debt`. Manually created or auto-detected.

```markdown
## Findings

- **Area**: {subsystem or module}
- **Debt type**: {duplication | complexity | coupling | obsolescence}
- **Impact**: {description of ongoing cost}
```

## Common Sections (All Sources)

These sections appear in every todo regardless of source.

```markdown
## Proposed Solutions

### Option 1: {Solution Name}

**Approach**: {description}
**Effort**: {estimate}
**Risk**: Low / Medium / High

## Recommended Action

_Filled during triage or auto-populated from TOME fix recommendation._

## Acceptance Criteria

- [ ] {criterion 1}
- [ ] {criterion 2}
- [ ] Tests pass
- [ ] Ward check clean

## Work Log

### {date} - Initial Discovery

**By**: {agent or user}
**Source**: {workflow that created this todo}

**Actions**:
- Created from {source_ref}

**Learnings**:
- {initial context}
```

## Work Log Entry Format

Each work session appends a new entry:

```markdown
### {date} - {phase description}

**By**: {agent name or user}

**Actions**:
- {what was done}
- {files modified with paths}

**Learnings**:
- {discoveries, gotchas, decisions}

**Subtasks**:
- [x] {completed item}
- [ ] {remaining item}
```
