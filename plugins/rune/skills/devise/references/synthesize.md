# Phase 2: Synthesize

After research completes, the Tarnished consolidates findings.

## Plan Detail Level Selection

Before drafting, ask the user for detail level:

```javascript
AskUserQuestion({
  questions: [{
    question: "What detail level for this plan?",
    header: "Detail",
    options: [
      { label: "Standard (Recommended)", description: "Overview, solution, technical approach, criteria, references" },
      { label: "Minimal", description: "Brief description + acceptance criteria only" },
      { label: "Comprehensive", description: "Full spec with phases, alternatives, risks, ERD, metrics" }
    ],
    multiSelect: false
  }]
})
```

## Consolidation

**Inputs**: research output files (paths from `tmp/plans/{timestamp}/research/`), selected detail level
**Outputs**: plan file (`plans/YYYY-MM-DD-{type}-{feature}-plan.md`)
**Preconditions**: git repository initialized (or gracefully handles non-git context)
**Error handling**: git commands wrapped in `2>/dev/null || echo "null"` for non-git directories; detached HEAD sets `branch` to `null`

1. Read all research output files from `tmp/plans/{timestamp}/research/`
2. Identify common themes, conflicting advice, key patterns
3. Populate git metadata in plan frontmatter: include `git_sha` (from `git rev-parse HEAD`) and `branch` (from `git branch --show-current`). If the working directory is not a git repository, omit these fields. On a detached HEAD, set `branch` to `null`.
4. Draft the plan document using the template matching the selected detail level:

## Minimal Template

```markdown
---
title: "{type}: {feature description}"
type: feat | fix | refactor
date: YYYY-MM-DD
version_target: "{estimated version}"
complexity: "{Low|Medium|High}"
estimated_effort: "{S|M|L|XL} — ~{N} LOC, {N} files"
impact: "{N}/10"
strategic_intent: "long-term"  # Options: long-term | quick-win | auto
non_goals: []  # List of explicitly out-of-scope items (from brainstorm or manual entry)
git_sha: !`git rev-parse HEAD 2>/dev/null || echo "null"`
branch: !`git branch --show-current 2>/dev/null | grep . || echo "null"`
session_budget:
  max_concurrent_agents: 3      # Cap on simultaneous teammates (applied silently); see sizing guide
---

# {Feature Title}

{Brief problem/feature description in 2-3 sentences}

## Acceptance Criteria

- [ ] Core requirement 1
- [ ] Core requirement 2

## Context

{Any critical information -- constraints, dependencies, deadlines}

## References

- Related: {links}
```

## Standard Template (default)

```markdown
---
title: "{type}: {feature description}"
type: feat | fix | refactor
date: YYYY-MM-DD
version_target: "{estimated version}"
complexity: "{Low|Medium|High}"
scope: "{description of files affected}"
risk: "{Low|Medium|High} — {brief explanation}"
estimated_effort: "{S|M|L|XL} — ~{N} LOC, {N} files"
impact: "{N}/10"
strategic_intent: "long-term"  # Options: long-term | quick-win | auto
non_goals: []  # List of explicitly out-of-scope items (from brainstorm or manual entry)
git_sha: !`git rev-parse HEAD 2>/dev/null || echo "null"`
branch: !`git branch --show-current 2>/dev/null | grep . || echo "null"`
session_budget:
  max_concurrent_agents: 5      # Cap on simultaneous teammates (applied silently); see sizing guide
---

# {Feature Title}

## Overview

{What and why -- informed by research findings}

## Problem Statement

{Why this matters, who is affected}

## Proposed Solution

{High-level approach informed by research}

## Solution Selection
{If Arena ran: include arena-selection findings below. If Arena was skipped but brainstorm ran: write "Approach selected during brainstorm — no competitive evaluation." If both Arena and brainstorm were skipped (--quick with direct feature description): omit this section entirely.}
- **Chosen approach**: {solution name} ({weighted score}/10, range 1-10)
- **Rationale**: {1-sentence why this approach won}
- **Top concern**: {highest-severity DA challenge}

## Technical Approach

{Implementation details referencing codebase patterns discovered by repo-surveyor}

### Stakeholders

{Who is affected: end users, developers, operations}

## Acceptance Criteria

- [ ] Functional requirement 1
- [ ] Functional requirement 2
- [ ] Testing requirement

## Non-Goals

{Explicitly out-of-scope items from brainstorm. Populate from `non_goals` frontmatter field.}
{(No brainstorm -- add manually if needed)}

- {item 1 -- why excluded}

## Success Criteria

{Measurable outcomes that determine whether this feature is successful. Distinct from Acceptance Criteria -- these measure business/user impact, not implementation completeness.}
{(No brainstorm -- add manually if needed)}

- {criterion 1 -- metric and target}

## Success Metrics

{How we measure success}

## Dependencies & Risks

{What could block or complicate this}

## Documentation Impact

Files that must be updated when this feature ships:

### Files Referencing This Feature
- [ ] {file}: {what reference needs updating}

### Count/Version Changes
- [ ] plugin.json: version bump to {target}
- [ ] CLAUDE.md: {count or version reference}
- [ ] README.md: {count or version reference}
- [ ] CHANGELOG.md: new entry for {version}

### Priority/Registry Updates
- [ ] {registry file}: add/update entry for {feature}

## Cross-File Consistency

Files that must stay in sync when this plan's changes are applied:

- [ ] Version: plugin.json, CLAUDE.md, README.md
- [ ] Counts: {list files where counts change}
- [ ] References: {list files that cross-reference each other}

## References

- Codebase patterns: {repo-surveyor findings}
- Past learnings: {echo-reader findings}
- Git history: {git-miner findings}
- Best practices: {practice-seeker findings, if run}
- Framework docs: {lore-scholar findings, if run}
- Cross-model research: {codex-researcher findings, if run}
- Spec analysis: {flow-seer findings}
```

## Comprehensive Template

```markdown
---
title: "{type}: {feature description}"
type: feat | fix | refactor
date: YYYY-MM-DD
version_target: "{estimated version}"
complexity: "{Low|Medium|High}"
scope: "{description of files affected}"
risk: "{Low|Medium|High} — {brief explanation}"
estimated_effort: "{S|M|L|XL} — ~{N} LOC, {N} files"
impact: "{N}/10"
strategic_intent: "long-term"  # Options: long-term | quick-win | auto
non_goals: []  # List of explicitly out-of-scope items (from brainstorm or manual entry)
git_sha: !`git rev-parse HEAD 2>/dev/null || echo "null"`
branch: !`git branch --show-current 2>/dev/null | grep . || echo "null"`
session_budget:
  max_concurrent_agents: 8      # Cap on simultaneous teammates (applied silently); see sizing guide
---

# {Feature Title}

## Overview

{Executive summary}

## Problem Statement

{Detailed problem analysis with stakeholder impact}

## Proposed Solution

{Comprehensive solution design}

## Technical Approach

### Architecture

{Detailed technical design}

> Each implementation phase that includes pseudocode must follow the Plan Section Convention (Inputs/Outputs/Preconditions/Error handling before code blocks).

### Implementation Phases

#### Phase 1: {Foundation}

- Tasks and deliverables
- Success criteria
- Effort estimate: {S/M/L}

#### Phase 2: {Core Implementation}

- Tasks and deliverables
- Success criteria
- Effort estimate: {S/M/L}

#### Phase 3: {Polish & Hardening}

- Tasks and deliverables
- Success criteria
- Effort estimate: {S/M/L}

### Data Model Changes

{ERD mermaid diagram if applicable}

~~~mermaid
erDiagram
    ENTITY_A ||--o{ ENTITY_B : has
~~~

## Solution Selection

### Arena Evaluation Matrix
{Full evaluation matrix from arena-matrix.md, if Arena ran}

### Alternative Approaches Considered
| Approach | Score | Top Concern | Why Not Selected |
|----------|-------|-------------|-----------------|
{Rejected arena solutions with scores and DA concerns}

## Acceptance Criteria

### Functional Requirements

- [ ] Detailed functional criteria

### Non-Functional Requirements

- [ ] Performance targets
- [ ] Security requirements

### Quality Gates

- [ ] Test coverage requirements
- [ ] Documentation completeness

## Non-Goals

{Explicitly out-of-scope items from brainstorm. Populate from `non_goals` frontmatter field.}
{(No brainstorm -- add manually if needed)}

- {item 1 -- why excluded}
- {item 2 -- why excluded}

## Success Criteria

{Measurable outcomes that determine whether this feature is successful. Distinct from Acceptance Criteria -- these measure business/user impact, not implementation completeness.}
{(No brainstorm -- add manually if needed)}

- {criterion 1 -- metric and target}
- {criterion 2 -- metric and target}

## Success Metrics

{Detailed KPIs and measurement methods}

## Dependencies & Prerequisites

{Detailed dependency analysis}

## Risk Analysis & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| {Risk 1} | H/M/L | H/M/L | {Strategy} |

## Cross-File Consistency

Files that must stay in sync when this plan's changes are applied:

### Version Strings
- [ ] plugin.json `version` field
- [ ] CLAUDE.md version reference
- [ ] README.md version badge / header

### Counts & Registries
- [ ] {list files where counts change}
- [ ] {list registry files that enumerate items}

### Cross-References
- [ ] {list files that reference each other}
- [ ] {list docs that cite the same source of truth}

### Talisman Sync
- [ ] talisman.example.yml reflects any new config fields
- [ ] CLAUDE.md configuration section matches talisman schema

## Documentation Impact & Plan

Files that must be updated when this feature ships:

### Files Referencing This Feature
- [ ] {file}: {what reference needs updating}

### Count/Version Changes
- [ ] plugin.json: version bump to {target}
- [ ] CLAUDE.md: {count or version reference}
- [ ] README.md: {count or version reference}
- [ ] CHANGELOG.md: new entry for {version}

### Priority/Registry Updates
- [ ] {registry file}: add/update entry for {feature}

### New Documentation
- [ ] {new doc file}: {purpose}

### Updated Documentation
- [ ] {existing doc}: {what changes}

### Inline Comments / Migration Guides
- [ ] {migration guide or inline comment updates}

## AI-Era Considerations (optional)

- AI tools used during research: {list tools and what they found}
- Prompts/patterns that worked well: {any useful prompt patterns}
- Areas needing human review: {sections that require domain expertise validation}
- Testing emphasis: {areas where AI-accelerated implementation needs extra testing}

## References

### Internal

- Architecture: {file_path:line_number}
- Similar features: {file_path:line_number}
- Past learnings: {echo findings}

### External

- Framework docs: {urls}
- Best practices: {urls}

### Related Work

- PRs: #{numbers}
- Issues: #{numbers}
```

## How to Fill New Header Fields

During Phase 2 Synthesize, after consolidating research:

1. **version_target**: Read current version from `plugins/rune/.claude-plugin/plugin.json`. For `type: feat`, bump minor. For `type: fix`, bump patch. Label as "estimated" since implementation may reveal scope changes.

2. **complexity**: Score based on task count (>=8 = High), file count (>=6 = High), cross-cutting concerns.

3. **scope** (Standard/Comprehensive only): Human-readable description of files affected. Format: "{N} files ({description})".

4. **risk** (Standard/Comprehensive only): Assess from research findings. Format: "{Low|Medium|High} — {brief explanation}". Note: The risk value includes quotes in YAML (see templates) — preserve them when filling.

**Size guide for `estimated_effort`:**

| Size | LOC Range | File Count | Examples |
|------|-----------|------------|----------|
| S    | < 200     | 1-2        | Bug fixes, minor refactors |
| M    | 200-800   | 2-4        | Feature additions, medium refactors |
| L    | 800-2000  | 4-8        | New subsystems, major features |
| XL   | > 2000    | 8+         | Architectural changes, multi-phase features |

5. **estimated_effort**: Size from scope + complexity. Format: "{S|M|L|XL} — ~{N} LOC, {N} files". Use the size guide table above.

6. **impact**: Score 1-10. Anchor points: 1 = cosmetic, 5 = useful improvement, 10 = critical blocker.

7. **strategic_intent**: Declare the plan's strategic intent. Options: `"long-term"` (default — build correctly, minimize future debt), `"quick-win"` (ship fast, accept trade-offs), `"auto"` (let horizon-sage infer from type + complexity + scope). When in doubt, leave as `"long-term"`.

8. **session_budget** (optional): Cap on simultaneous agent teammates spawned during `strive`/`arc` execution. Set `max_concurrent_agents` based on plan effort using the sizing guide below. The cap is applied silently — workers respect it without surfacing it to the user.

```yaml
session_budget:
  max_concurrent_agents: 8       # Cap on simultaneous teammates (applied silently)
```

**Sizing guide for `max_concurrent_agents`:**

| Plan Effort | max_concurrent_agents |
|-------------|----------------------|
| S (<200 LOC) | 3 |
| M (200-800 LOC) | 5 |
| L (800-2000 LOC) | 8 |
| XL (>2000 LOC) | 12 (with shatter, per shard) |

## Formatting Best Practices

- Use collapsible `<details>` sections for lengthy logs or optional context
- Add syntax-highlighted code blocks with file path references: `app/services/foo.rb:42`
- Cross-reference related issues with `#number`, commits with SHA hashes
- For model changes, include ERD mermaid diagrams
- Code examples in plans are illustrative pseudocode. Sections with pseudocode include contract headers (Inputs/Outputs/Preconditions/Error handling) per the Plan Section Convention below

## Plan Section Convention -- Contracts Before Code

When a plan section includes pseudocode (JavaScript/Bash code blocks), include contract headers BEFORE the code block.

**Required structure for sections with pseudocode:**

```
## Section Name

**Inputs**: List all variables this section consumes (name, type, where defined)
**Outputs**: What this section produces (artifacts, state changes, return values)
**Preconditions**: What must be true before this section runs
**Error handling**: How failures are handled (for each Bash/external call)

```javascript
// Pseudocode -- illustrative only
// All variables must appear in Inputs list above (or be defined in this block)
// All Bash() calls must have error handling described above
```
```

**Rules for pseudocode in plans:**
1. Every variable used in a code block must either appear in the **Inputs** list or be defined within the block
2. Every `Bash()` call must have a corresponding entry in **Error handling**
3. Every helper function called (e.g., `extractPlanTitle()`) must either be defined in the plan or listed as "defined by worker" in **Inputs**
4. Pseudocode is *illustrative* -- workers implement from the contract (Inputs/Outputs/Preconditions), using pseudocode as guidance

**Example (good):**

```
## Phase 6.5: Ship

**Inputs**: currentBranch (string, from Phase 0.5), defaultBranch (string, from Phase 0.5),
planPath (string, from Phase 0), completedTasks (Task[], from TaskList before TeamDelete),
wardResults ({name, exitCode}[], from Phase 4)
**Outputs**: PR URL (string) or skip message; branch pushed to origin
**Preconditions**: On feature branch (not default), gh CLI authenticated
**Error handling**: git push failure -> warn + manual command; gh pr create failure -> warn (branch already pushed)

```javascript
// Validate branch before shell interpolation
// Push branch with error check
// Generate PR title from plan frontmatter (sanitize for shell safety)
// Build PR body from completedTasks + wardResults + diffStat
// Write body to file (not -m flag), create PR via gh CLI
```
```

**Example (bad -- causes bugs):**

```
## Phase 6.5: Ship

```javascript
const planTitle = extractPlanTitle(planPath)  // <- undefined function
const prTitle = `${planType}: ${planTitle}`    // <- planType undefined
Bash(`git push -u origin "${currentBranch}"`)  // <- no error handling
```
```

5. Write to `plans/YYYY-MM-DD-{type}-{feature-name}-plan.md`

6. **Comprehensive only -- Second SpecFlow pass**: If detail level is Comprehensive, re-run flow-seer on the drafted plan (not just the raw spec from Phase 1D). Write to `tmp/plans/{timestamp}/research/specflow-post-draft.md`. Tarnished appends findings to the plan before scroll-reviewer runs.
