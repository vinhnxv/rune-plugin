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

1. Read all research output files from `tmp/plans/{timestamp}/research/`
2. Identify common themes, conflicting advice, key patterns
3. Draft the plan document using the template matching the selected detail level:

## Minimal Template

```markdown
---
title: "{type}: {feature description}"
type: feat | fix | refactor
date: YYYY-MM-DD
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
---

# {Feature Title}

## Overview

{What and why -- informed by research findings}

## Problem Statement

{Why this matters, who is affected}

## Proposed Solution

{High-level approach informed by research}

## Solution Selection
{If Arena ran: include arena-selection findings below. If Arena was skipped (--quick, --no-arena, bug fix): omit this section or write "Approach selected during brainstorm — no competitive evaluation."}
- **Chosen approach**: {solution name} ({weighted score}/10)
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

<!-- NOTE: Remove space in "` ``" fences when using this template -->
` ``mermaid
erDiagram
    ENTITY_A ||--o{ ENTITY_B : has
` ``

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

4. Write to `plans/YYYY-MM-DD-{type}-{feature-name}-plan.md`

5. **Comprehensive only -- Second SpecFlow pass**: If detail level is Comprehensive, re-run flow-seer on the drafted plan (not just the raw spec from Phase 1D). Write to `tmp/plans/{timestamp}/research/specflow-post-draft.md`. Tarnished appends findings to the plan before scroll-reviewer runs.
