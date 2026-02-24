# Dependency Patterns — strive Task Graph Reference

Named patterns for structuring task dependencies in `/rune:strive` Phase 1.
Use these patterns when designing `blockedBy` relationships between tasks.

## 5 Named Patterns

### 1. Fully Independent

All tasks can run in parallel with no dependencies.

```
A     B     C     D
│     │     │     │
▼     ▼     ▼     ▼
(all complete independently)
```

**Use when**: No shared files or state between tasks. Each task modifies separate files.
**blockedBy**: `[]` for all tasks.
**Example**: Adding unrelated utility functions to different modules.

---

### 2. Sequential Chain

Tasks execute in strict order: A must complete before B starts.

```
A → B → C → D
```

**Use when**: Each task depends on the previous task's output (e.g., model → service → controller → route).
**blockedBy**: `B: [A], C: [B], D: [C]`
**Example**: Database migration → model update → service update → API endpoint.

---

### 3. Diamond

Fork from a shared root, then join at a common successor.

```
    A
   / \
  B   C
   \ /
    D
```

**Use when**: Two tasks share a common prerequisite and a common consumer.
**blockedBy**: `B: [A], C: [A], D: [B, C]`
**Example**: A creates shared types, B implements feature-X, C implements feature-Y, D writes integration tests for both.

---

### 4. Fork-Join

Multiple parallel paths converge at a single synchronization point.

```
      A
    / | \
   B  C  D
    \ | /
      E
```

**Use when**: Setup task enables multiple independent implementations, followed by a validation/integration step.
**blockedBy**: `B: [A], C: [A], D: [A], E: [B, C, D]`
**Example**: A scaffolds project structure, B-D implement independent features, E runs full test suite.

---

### 5. Pipeline

Streaming parallel pipelines where corresponding stages run in parallel.

```
A₁ → B₁
A₂ → B₂
A₃ → B₃
```

**Use when**: Multiple independent feature tracks, each with their own implementation-then-test sequence.
**blockedBy**: `B₁: [A₁], B₂: [A₂], B₃: [A₃]`
**Example**: Three independent API endpoints, each with implementation + test tasks.

---

## 3 Anti-Patterns

### 1. Circular Dependency

```
A → B → C → A   (deadlock!)
```

**Problem**: Creates a deadlock — no task can start because each waits on the next.
**Detection**: If during Phase 1 you detect a cycle in `blockedBy`, it is a plan error.
**Fix**: Break the cycle by identifying the shared resource. Extract it into a new prerequisite task that all cycle members depend on.

---

### 2. Unnecessary Dependencies

```
A → B → C → D → E   (over-serialized)
```

**Problem**: Tasks that could run in parallel are serialized, wasting worker capacity.
**Detection**: If task B does not read or write any file that task A modifies, the dependency is unnecessary.
**Fix**: Only add `blockedBy` when tasks share file targets (detected by `extractFileTargets()` set intersection in Phase 1). Remove dependencies between tasks with disjoint file sets.

---

### 3. Star Bottleneck

```
    A
  / | \
 B  C  D
  \ | /
    E
  / | \
 F  G  H
```

**Problem**: Task E becomes a bottleneck — all downstream work waits on a single task.
**Detection**: One task appears in `blockedBy` of 3+ other tasks AND has 3+ blockers itself.
**Fix**: Decompose the bottleneck task into smaller independent pieces. If E validates B, C, and D independently, split into E₁, E₂, E₃ — each validating one upstream task.

---

## Choosing a Pattern

| Question | If Yes → Pattern |
|----------|-----------------|
| Do any tasks share files? | Use Diamond or Sequential Chain for shared-file tasks |
| Are all tasks independent? | Fully Independent |
| Is there a setup → parallel → validation flow? | Fork-Join |
| Are there N independent feature tracks? | Pipeline |
| Is one task blocking everything? | Refactor to avoid Star Bottleneck |
