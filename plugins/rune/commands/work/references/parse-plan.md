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

## Confirm with User

Present extracted tasks and ask for confirmation:

```
Extracted {N} tasks from plan:

Implementation:
  1. Write User model
  3. Write UserService (depends on #1)
  5. Write API routes (depends on #3)

Tests:
  2. Write User model tests
  4. Write UserService tests (depends on #3)
  6. Write API route tests (depends on #5)

Proceed with {N} tasks and {W} workers?
```
