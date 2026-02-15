# Parse Plan — work.md Phase 0 Reference

Task extraction and parsing from plan files.

## Find Plan

If no plan specified:
```bash
ls -t plans/*.md 2>/dev/null | head -5
```

If multiple found, ask user which to execute. If none found, suggest `/rune:plan` first.

## Validate Plan Path

```javascript
// Validate plan path before any Read or display
if (!/^[a-zA-Z0-9._\/-]+$/.test(planPath) || planPath.includes('..')) {
  throw new Error(`Invalid plan path: ${planPath}`)
}
```

## Extract Tasks

Read the plan and extract implementation tasks:

1. Look for checkbox items (`- [ ]`), numbered lists, or "Tasks" sections
2. Identify dependencies between tasks (Phase ordering, explicit "depends on" references)
3. Classify each task:
   - **Implementation task**: Writing code (assigned to rune-smith)
   - **Test task**: Writing tests (assigned to trial-forger)
   - **Independent**: Can run in parallel
   - **Sequential**: Must wait for dependencies

```javascript
tasks = [
  { subject: "Write User model", type: "impl", blockedBy: [] },
  { subject: "Write User model tests", type: "test", blockedBy: [] },
  { subject: "Write UserService", type: "impl", blockedBy: ["#1"] },
  { subject: "Write UserService tests", type: "test", blockedBy: ["#3"] },
  { subject: "Write API routes", type: "impl", blockedBy: ["#3"] },
  { subject: "Write API route tests", type: "test", blockedBy: ["#5"] },
]
```

## Previous Shard Context (Multi-Shard Plans Only)

When the plan is a shard (filename matches `*-shard-N-*`), inject context from completed sibling shards into worker prompts.

**Inputs**: planPath (string), dirname/basename (stdlib path utilities)
**Outputs**: shardContext (string, injected into worker prompts in Phase 2)
**Preconditions**: Plan file exists and matches shard naming pattern (`-shard-\d+-`)
**Error handling**: Read(sibling) failure -> skip sibling, log warning, continue with remaining shards

```javascript
const shardMatch = planPath.match(/-shard-(\d+)-/)
if (shardMatch) {
  const shardNum = parseInt(shardMatch[1])
  const planDir = dirname(planPath)
  const planBase = basename(planPath).replace(/-shard-\d+-[^-]+-plan\.md$/, '')

  const siblingShards = Glob(`${planDir}/${planBase}-shard-*-plan.md`)
    .filter(p => {
      const n = parseInt(p.match(/-shard-(\d+)-/)?.[1] ?? "0")
      return n < shardNum
    })
    .sort()

  let shardContext = ""
  for (const sibling of siblingShards) {
    const content = Read(sibling)
    const checked = content.match(/- \[x\].+/g) || []
    const techMatch = content.match(/## Technical Approach\n([\s\S]{0,500})/)
    shardContext += `\n### Shard: ${basename(sibling)}\nCompleted: ${checked.length} criteria\n`
    if (techMatch) shardContext += `Patterns: ${techMatch[1].trim().slice(0, 300)}\n`
  }
  // shardContext is injected into worker spawn prompts (Phase 2) as:
  // "PREVIOUS SHARD CONTEXT:\n{shardContext}\nReuse patterns from earlier shards."
}
```

## Identify Ambiguities

After extracting tasks, scan for potential issues before asking the user to confirm:

1. **Vague task descriptions**: Tasks with no file references, no acceptance criteria, or generic verbs ("improve", "update", "handle")
2. **Missing dependencies**: Tasks that reference components not covered by other tasks
3. **Unclear scope**: Tasks where the plan says "etc." or "and similar"
4. **Conflicting instructions**: Tasks where the plan gives contradictory guidance

If ambiguities found (>= 1):
```javascript
AskUserQuestion({
  questions: [{
    question: `Found ${count} ambiguities in the plan:\n${ambiguityList}\n\nClarify now or proceed as-is?`,
    header: "Clarify",
    options: [
      { label: "Clarify now (Recommended)", description: "Answer questions before workers start" },
      { label: "Proceed as-is", description: "Workers will interpret ambiguities on their own" }
    ],
    multiSelect: false
  }]
})
```

If user chooses to clarify: ask specific questions one at a time (max 3), then append clarifications to task descriptions before creating the task pool. Default on timeout: "Proceed as-is" (fail-safe).

## Risk Tier Classification

After extracting tasks, classify each task's risk tier using the deterministic decision tree from `risk-tiers.md`. This MUST happen before task creation.

```javascript
// SYNC: risk-tier-paths — update both this function AND risk-tiers.md File-Path Fallback Heuristic table
function classifyRiskTier(task) {
  const desc = (task.subject + " " + task.description).toLowerCase()
  const files = task.fileTargets || []

  // Q1: Auth/security/encryption/credentials?
  // Conservative: over-classifies to higher tier. Manual override via plan metadata if needed.
  if (/\b(auth|security|encrypt|credential|secret|token|password|oauth|jwt)\b/.test(desc)
      || files.some(f => /(auth|security|crypto|credentials)/.test(f))) {
    return { tier: 3, name: "Elden" }
  }
  // Q2: DB schemas/migrations/CI-CD/infrastructure?
  // Conservative: over-classifies to higher tier. Manual override via plan metadata if needed.
  if (/\b(migrat|schema|deploy|ci[\/-]cd|infrastructure|database|pipeline)\b/.test(desc)
      || files.some(f => /(migrations|deploy|\.github|infra)/.test(f))) {
    return { tier: 2, name: "Rune" }
  }
  // Q3: User-facing behavior (API/UI/validation/errors)?
  if (/\b(api|route|endpoint|component|view|ui|validation|response|request)\b/.test(desc)
      || files.some(f => /(api|routes|components|views)/.test(f))) {
    return { tier: 1, name: "Ember" }
  }
  // Q4: Internal only (rename/comments/formatting/tests/docs)?
  if (/\b(test|doc|comment|format|rename|refactor|lint|readme|changelog)\b/.test(desc)
      || files.some(f => /(tests|docs|__mocks__)/.test(f) || /\.md$/.test(f))) {
    return { tier: 0, name: "Grace" }
  }
  // Default: Tier 1 (caution)
  return { tier: 1, name: "Ember" }
}
```

## File Target Extraction

Extract file paths mentioned in task descriptions to enable ownership conflict detection:

```javascript
function extractFileTargets(task) {
  const desc = task.subject + " " + (task.description || "")
  // Match file-like patterns: src/foo/bar.ts, path/to/file.py, etc.
  const filePattern = /(?:^|\s)([\w./-]+\.\w{1,10})\b/g
  const dirPattern = /(?:^|\s)([\w./-]+\/)\b/g
  const files = new Set()
  for (const match of desc.matchAll(filePattern)) {
    const path = match[1]
    if (path.includes('/') && !path.startsWith('http')) files.add(path)
  }
  // Post-match filter: remove false positives that look like file paths but aren't
  // (a) version strings like "v2.0", "1.2.3", (b) abbreviations like "e.g.", "i.e.", "etc.",
  // (c) URLs that slipped through the http check
  const falsePositiveFilter = (p) =>
    /^v?\d+\.\d+/.test(p) ||                     // version strings
    /^(e\.g|i\.e|etc|vs|ca|approx)\./i.test(p) || // common abbreviations
    /^https?:/.test(p) ||                          // URLs
    /\.\./.test(p)                                 // path traversal (..) — reject any path with parent refs
  for (const f of files) {
    if (falsePositiveFilter(f)) files.delete(f)
  }
  // Directory-level ownership as fallback
  const dirs = new Set()
  for (const match of desc.matchAll(dirPattern)) {
    dirs.add(match[1])
  }
  return { files: [...files], dirs: [...dirs] }
}
```

For tasks with no extractable file targets, no ownership restriction is applied (treated as shared).

## Confirm with User

Present extracted tasks with risk tiers and ask for confirmation:

```
Extracted {N} tasks from plan:

Implementation:
  1. [Tier 0: Grace] Write User model — src/models/
  3. [Tier 1: Ember] Write UserService (depends on #1) — src/services/user.ts
  5. [Tier 1: Ember] Write API routes (depends on #3) — src/api/users.ts

Tests:
  2. [Tier 0: Grace] Write User model tests — tests/
  4. [Tier 0: Grace] Write UserService tests (depends on #3) — tests/
  6. [Tier 0: Grace] Write API route tests (depends on #5) — tests/

Proceed with {N} tasks and {W} workers?
```
