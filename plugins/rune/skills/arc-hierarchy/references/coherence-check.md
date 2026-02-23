# Coherence Check Reference

Pre-execution validation for hierarchical plan decompositions. Validates that child plans collectively implement all parent plan requirements, that contracts are internally consistent, and that the dependency DAG is acyclic.

**Linked from**: `/rune:devise` Phase 2.6 (optional post-shatter audit), and `arc-hierarchy` Phase 4.

**Output**: `tmp/plans/{timestamp}/coherence-check.md`

---

## runCoherenceCheck(planContent, executionTable, contractMatrix)

Master check that runs all sub-checks and aggregates results.

**Inputs**:
- `planContent` — full string content of the parent plan
- `executionTable` — output of `parseExecutionTable()`
- `contractMatrix` — output of `parseDependencyContractMatrix()`

**Outputs**: `{ errors: CoherenceIssue[], warnings: CoherenceIssue[], autoFixed: string[] }`
  where `CoherenceIssue = { severity: "error"|"warning", category: string, message: string, fix?: string }`
**Error handling**: Individual check failures are caught and reported as errors — never crash the overall check.

```javascript
function runCoherenceCheck(planContent, executionTable, contractMatrix) {
  const errors = []
  const warnings = []
  const autoFixed = []

  try {
    // Check 1: Task coverage (parent ACs → child mapping)
    const coverageResult = checkTaskCoverage(planContent, executionTable)
    errors.push(...coverageResult.errors)
    warnings.push(...coverageResult.warnings)
    autoFixed.push(...coverageResult.autoFixed)
  } catch (e) {
    errors.push({ severity: "error", category: "COVERAGE", message: `Coverage check failed: ${e.message}` })
  }

  try {
    // Check 2: Contract integrity (requires/provides matching)
    const contractResult = checkContractIntegrity(contractMatrix)
    errors.push(...contractResult.errors)
    warnings.push(...contractResult.warnings)
  } catch (e) {
    errors.push({ severity: "error", category: "CONTRACT", message: `Contract check failed: ${e.message}` })
  }

  try {
    // Check 3: Duplicate task detection
    const dupeResult = checkDuplicateTasks(executionTable)
    warnings.push(...dupeResult.warnings)
  } catch (e) {
    warnings.push({ severity: "warning", category: "DUPLICATE", message: `Duplicate check failed: ${e.message}` })
  }

  try {
    // Check 4: Cross-cutting concern allocation
    const crossCutResult = checkCrossCuttingConcerns(planContent, executionTable)
    warnings.push(...crossCutResult.warnings)
  } catch (e) {
    warnings.push({ severity: "warning", category: "CROSS-CUT", message: `Cross-cutting check failed: ${e.message}` })
  }

  try {
    // Check 5: DAG validity (no backward deps, no self-deps — BUG-7)
    const dagResult = checkDependencyDAG(executionTable)
    errors.push(...dagResult.errors)
    warnings.push(...dagResult.warnings)
  } catch (e) {
    errors.push({ severity: "error", category: "DAG", message: `DAG validation failed: ${e.message}` })
  }

  // Write output report
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
  const reportPath = `tmp/plans/${timestamp}/coherence-check.md`
  Bash(`mkdir -p "tmp/plans/${timestamp}"`)
  Write(reportPath, formatCoherenceReport({ errors, warnings, autoFixed, timestamp }))

  log(`Coherence check complete. Report: ${reportPath}`)
  log(`  Errors: ${errors.length}, Warnings: ${warnings.length}, Auto-fixed: ${autoFixed.length}`)

  return { errors, warnings, autoFixed, reportPath }
}
```

---

## Check 1: Task Coverage

Verify that every acceptance criterion in the parent plan is addressed by at least one child plan.

```javascript
function checkTaskCoverage(planContent, executionTable) {
  const errors = []
  const warnings = []
  const autoFixed = []

  // Extract ACs from parent plan: lines starting with "- [ ]" or "- [x]" under ## Acceptance Criteria
  const acSection = planContent.match(/## Acceptance Criteria([\s\S]*?)(?=\n##|\Z)/i)?.[1] || ""
  const parentACs = acSection
    .split("\n")
    .filter(line => line.trim().match(/^-\s+\[[ x]\]/))
    .map(line => line.trim().replace(/^-\s+\[[ x]\]\s+/, ""))

  if (parentACs.length === 0) {
    warnings.push({
      severity: "warning",
      category: "COVERAGE",
      message: "Parent plan has no ## Acceptance Criteria section. Cannot verify task coverage."
    })
    return { errors, warnings, autoFixed }
  }

  // Read each child plan and extract their ACs
  const childACs = new Map()  // child path → string[]
  for (const entry of executionTable) {
    try {
      const childContent = Read(entry.path)
      if (!childContent) continue
      const childAcSection = childContent.match(/## Acceptance Criteria([\s\S]*?)(?=\n##|\Z)/i)?.[1] || ""
      const acs = childAcSection
        .split("\n")
        .filter(line => line.trim().match(/^-\s+\[[ x]\]/))
        .map(line => line.trim().replace(/^-\s+\[[ x]\]\s+/, ""))
      childACs.set(entry.path, acs)
    } catch (e) {
      warnings.push({ severity: "warning", category: "COVERAGE", message: `Cannot read child plan: ${entry.path}` })
    }
  }

  // Check each parent AC appears in at least one child (fuzzy match: >60% word overlap)
  const allChildACs = Array.from(childACs.values()).flat()
  const orphanACs = []

  for (const parentAC of parentACs) {
    const covered = allChildACs.some(childAC => wordOverlap(parentAC, childAC) > 0.6)
    if (!covered) {
      orphanACs.push(parentAC)
    }
  }

  if (orphanACs.length > 0) {
    errors.push({
      severity: "error",
      category: "COVERAGE",
      message: `${orphanACs.length} parent AC(s) not covered by any child plan:`,
      details: orphanACs
    })
  }

  return { errors, warnings, autoFixed }
}

// Word overlap ratio between two strings (Jaccard similarity on word sets)
function wordOverlap(a, b) {
  const wordsA = new Set(a.toLowerCase().split(/\s+/).filter(w => w.length > 2))
  const wordsB = new Set(b.toLowerCase().split(/\s+/).filter(w => w.length > 2))
  if (wordsA.size === 0 || wordsB.size === 0) return 0
  const intersection = new Set([...wordsA].filter(w => wordsB.has(w)))
  const union = new Set([...wordsA, ...wordsB])
  return intersection.size / union.size
}
```

---

## Check 2: Contract Integrity

Verify that every `requires` entry has a matching `provides` entry somewhere in the matrix.

```javascript
function checkContractIntegrity(contractMatrix) {
  const errors = []
  const warnings = []

  // Build a complete set of provided artifacts
  const allProvides = new Map()  // `type:name` → providing child
  for (const entry of contractMatrix) {
    for (const artifact of entry.provides) {
      const key = `${artifact.type}:${artifact.name}`
      allProvides.set(key, entry.child)
    }
  }

  // Check each requires has a matching provide
  for (const entry of contractMatrix) {
    for (const artifact of entry.requires) {
      if (artifact.optional) continue  // Optional — no matching provides required

      const key = `${artifact.type}:${artifact.name}`
      if (!allProvides.has(key)) {
        errors.push({
          severity: "error",
          category: "CONTRACT",
          message: `Child "${entry.child}" requires ${key} but no child provides it.`,
          fix: `Add "${key}" to a predecessor child's provides list.`
        })
      }
    }
  }

  // Warn about provided artifacts that nothing requires (might be fine, but worth noting)
  const allRequires = new Set()
  for (const entry of contractMatrix) {
    for (const artifact of entry.requires) {
      allRequires.add(`${artifact.type}:${artifact.name}`)
    }
  }
  for (const [key, provider] of allProvides) {
    if (!allRequires.has(key)) {
      warnings.push({
        severity: "warning",
        category: "CONTRACT",
        message: `Child "${provider}" provides ${key} but nothing requires it (may be external dependency or future use).`
      })
    }
  }

  return { errors, warnings }
}
```

---

## Check 3: Duplicate Task Detection

Detect child plans with >80% word overlap in their task descriptions — likely duplicated work.

```javascript
function checkDuplicateTasks(executionTable) {
  const warnings = []
  const DUPLICATE_THRESHOLD = 0.8

  // Load all child plan titles and AC lists
  const childSummaries = []
  for (const entry of executionTable) {
    try {
      const content = Read(entry.path)
      if (!content) continue
      const title = content.match(/^#\s+(.+)/m)?.[1] || entry.path
      const acSection = content.match(/## Acceptance Criteria([\s\S]*?)(?=\n##|\Z)/i)?.[1] || ""
      childSummaries.push({ seq: entry.seq, path: entry.path, title, acSection })
    } catch (e) {
      // Skip unreadable files
    }
  }

  // Compare all pairs
  for (let i = 0; i < childSummaries.length; i++) {
    for (let j = i + 1; j < childSummaries.length; j++) {
      const a = childSummaries[i]
      const b = childSummaries[j]
      const overlap = wordOverlap(a.acSection, b.acSection)
      if (overlap > DUPLICATE_THRESHOLD) {
        warnings.push({
          severity: "warning",
          category: "DUPLICATE",
          message: `Children [${a.seq}] and [${b.seq}] have ${Math.round(overlap * 100)}% word overlap in ACs — possible duplicate work.`,
          details: [`${a.path}`, `${b.path}`]
        })
      }
    }
  }

  return { warnings }
}
```

---

## Check 4: Cross-Cutting Concern Allocation

Detect cross-cutting concerns (auth, logging, error handling, testing) that should be explicitly assigned to a child plan.

```javascript
function checkCrossCuttingConcerns(planContent, executionTable) {
  const warnings = []

  const CROSS_CUTTING_PATTERNS = [
    { name: "authentication/authorization", pattern: /\b(auth|authentication|authorization|jwt|session|rbac)\b/i },
    { name: "logging/observability",        pattern: /\b(logging|logger|observability|tracing|metrics|telemetry)\b/i },
    { name: "error handling",              pattern: /\b(error.?handling|try.catch|exception|retry|resilience)\b/i },
    { name: "testing infrastructure",      pattern: /\b(test.?infra|test.?setup|mock|stub|fixture|test.?util)\b/i },
    { name: "database migrations",         pattern: /\b(migration|schema.?change|db.?init|seed)\b/i }
  ]

  // Find cross-cutting mentions in parent plan
  const parentMentions = CROSS_CUTTING_PATTERNS.filter(cc => cc.pattern.test(planContent))

  for (const cc of parentMentions) {
    // Check if any child plan explicitly addresses this concern
    const addressed = executionTable.some(entry => {
      try {
        const content = Read(entry.path)
        return content && cc.pattern.test(content)
      } catch {
        return false
      }
    })

    if (!addressed) {
      warnings.push({
        severity: "warning",
        category: "CROSS-CUT",
        message: `Cross-cutting concern "${cc.name}" mentioned in parent plan but not explicitly addressed in any child plan.`,
        fix: `Add a dedicated child plan or explicit task for ${cc.name}.`
      })
    }
  }

  return { warnings }
}
```

---

## Check 5: DAG Validity (BUG-7)

Detect invalid dependency structures: self-dependencies and backward dependencies (where a child depends on a child with a higher sequence number that hasn't run yet in forward order).

```javascript
function checkDependencyDAG(executionTable) {
  const errors = []
  const warnings = []

  // Build seq → index map for ordering
  const seqIndex = new Map()
  for (let i = 0; i < executionTable.length; i++) {
    seqIndex.set(normalizeSeq(executionTable[i].seq), i)
  }

  for (const entry of executionTable) {
    const entryIdx = seqIndex.get(normalizeSeq(entry.seq))

    for (const dep of entry.dependencies) {
      const normalizedDep = normalizeSeq(dep)

      // Self-dependency (BUG-7)
      if (normalizedDep === normalizeSeq(entry.seq)) {
        errors.push({
          severity: "error",
          category: "DAG",
          message: `Child [${entry.seq}] has a self-dependency (depends on itself).`,
          fix: `Remove "${dep}" from [${entry.seq}]'s Dependencies column.`
        })
        continue
      }

      // Dependency on non-existent child
      if (!seqIndex.has(normalizedDep)) {
        errors.push({
          severity: "error",
          category: "DAG",
          message: `Child [${entry.seq}] depends on [${dep}] which does not exist in the execution table.`,
          fix: `Check that seq "${dep}" exists in the execution table.`
        })
        continue
      }

      const depIdx = seqIndex.get(normalizedDep)

      // Backward dependency: depending on a later-sequenced child (not necessarily wrong but suspicious)
      if (depIdx > entryIdx) {
        warnings.push({
          severity: "warning",
          category: "DAG",
          message: `Child [${entry.seq}] depends on [${dep}] which is sequenced AFTER it. This creates a forward reference that may not execute correctly.`,
          fix: `Reorder execution table so [${dep}] appears before [${entry.seq}], or reconsider the dependency direction.`
        })
      }
    }
  }

  // Cycle detection via DFS
  const visited = new Set()
  const inStack = new Set()

  function dfsCycleCheck(seq) {
    visited.add(seq)
    inStack.add(seq)

    const entry = executionTable.find(e => normalizeSeq(e.seq) === seq)
    if (!entry) return false

    for (const dep of entry.dependencies) {
      const normDep = normalizeSeq(dep)
      if (!visited.has(normDep)) {
        if (dfsCycleCheck(normDep)) return true
      } else if (inStack.has(normDep)) {
        return true
      }
    }

    inStack.delete(seq)
    return false
  }

  for (const entry of executionTable) {
    const normSeq = normalizeSeq(entry.seq)
    if (!visited.has(normSeq)) {
      if (dfsCycleCheck(normSeq)) {
        errors.push({
          severity: "error",
          category: "DAG",
          message: `Circular dependency detected involving child [${entry.seq}].`,
          fix: "Break the cycle by removing one of the dependency links."
        })
      }
    }
  }

  return { errors, warnings }
}
```

---

## Auto-Fix Strategies

Some issues can be auto-fixed without user intervention.

```javascript
function applyAutoFixes(planContent, checkResult) {
  const fixed = []
  let content = planContent

  for (const error of checkResult.errors) {
    if (error.category === "DAG" && error.autoFix === "remove-self-dep") {
      // Auto-remove self-dependency from table
      const seqMatch = error.message.match(/\[(\w+)\] has a self-dependency/)
      if (seqMatch) {
        const seq = seqMatch[1]
        content = content.replace(
          new RegExp(`(\\|\\s*${escapeRegex(seq)}\\s*\\|[^|]+\\|[^|]+\\|)\\s*${escapeRegex(seq)}\\s*(\\|)`),
          `$1 — $2`
        )
        fixed.push(`Auto-fixed: removed self-dependency from [${seq}]`)
      }
    }
  }

  return { content, fixed }
}
```

---

## Report Format

```javascript
function formatCoherenceReport({ errors, warnings, autoFixed, timestamp }) {
  const lines = [
    `# Coherence Check Report`,
    ``,
    `Generated: ${timestamp}`,
    ``,
    `## Summary`,
    ``,
    `| Category | Count |`,
    `|----------|-------|`,
    `| Errors (blocking) | ${errors.length} |`,
    `| Warnings (non-blocking) | ${warnings.length} |`,
    `| Auto-fixed | ${autoFixed.length} |`,
    ``
  ]

  if (errors.length > 0) {
    lines.push(`## Errors (Blocking)`, ``)
    for (const e of errors) {
      lines.push(`### [${e.category}] ${e.message}`)
      if (e.details) lines.push(...e.details.map(d => `- ${d}`))
      if (e.fix) lines.push(`**Fix**: ${e.fix}`)
      lines.push(``)
    }
  }

  if (warnings.length > 0) {
    lines.push(`## Warnings`, ``)
    for (const w of warnings) {
      lines.push(`### [${w.category}] ${w.message}`)
      if (w.details) lines.push(...w.details.map(d => `- ${d}`))
      if (w.fix) lines.push(`**Suggestion**: ${w.fix}`)
      lines.push(``)
    }
  }

  if (autoFixed.length > 0) {
    lines.push(`## Auto-Fixed`, ``)
    for (const fix of autoFixed) {
      lines.push(`- ${fix}`)
    }
    lines.push(``)
  }

  return lines.join("\n")
}
```
