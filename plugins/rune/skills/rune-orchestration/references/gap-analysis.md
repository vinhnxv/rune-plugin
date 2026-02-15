# Phase 5.5: Implementation Gap Analysis — Full Algorithm

Deterministic, orchestrator-only check that cross-references the plan's acceptance criteria against committed code changes. Zero LLM cost.

**Team**: None (orchestrator-only)
**Tools**: Read, Glob, Grep, Bash (git diff, grep)
**Timeout**: 60 seconds

## STEP 1: Extract Acceptance Criteria

```javascript
const enrichedPlan = Read(`tmp/arc/${id}/enriched-plan.md`)
// Parse lines matching: "- [ ] " or "- [x] " (checklist items)
// Also parse lines matching: "**Acceptance criteria**:" section content
// Also parse "**Outputs**:" lines from Plan Section Convention headers
const criteria = extractAcceptanceCriteria(enrichedPlan)
// Returns: [{ text: string, checked: boolean, section: string }]

if (criteria.length === 0) {
  const skipReport = "# Gap Analysis\n\nNo acceptance criteria found in plan. Skipped."
  Write(`tmp/arc/${id}/gap-analysis.md`, skipReport)
  updateCheckpoint({
    phase: "gap_analysis",
    status: "completed",
    artifact: `tmp/arc/${id}/gap-analysis.md`,
    artifact_hash: sha256(skipReport),
    phase_sequence: 5.5,
    team_name: null
  })
  continue
}
```

## STEP 2: Get Committed Files from Work Phase

```javascript
const workSummary = Read(`tmp/arc/${id}/work-summary.md`)
const committedFiles = extractCommittedFiles(workSummary)
// Also: git diff --name-only {default_branch}...HEAD for ground truth
const diffResult = Bash(`git diff --name-only "${defaultBranch}...HEAD"`)
const diffFiles = diffResult.stdout.trim().split('\n').filter(f => f.length > 0)
```

## STEP 3: Cross-Reference Criteria Against Changes

```javascript
const gaps = []
// CDX-002 FIX: Sanitize diffFiles before use in shell commands (same filter as STEP 4.7)
const safeDiffFiles = diffFiles.filter(f => /^[a-zA-Z0-9._\-\/]+$/.test(f) && !f.includes('..'))
for (const criterion of criteria) {
  const identifiers = extractIdentifiers(criterion.text)

  let status = "UNKNOWN"
  for (const identifier of identifiers) {
    if (!/^[a-zA-Z0-9._\-\/]+$/.test(identifier)) continue
    if (safeDiffFiles.length === 0) break
    const grepResult = Bash(`rg -l --max-count 1 -- "${identifier}" ${safeDiffFiles.map(f => `"${f}"`).join(' ')} 2>/dev/null`)
    if (grepResult.stdout.trim().length > 0) {
      status = criterion.checked ? "ADDRESSED" : "PARTIAL"
      break
    }
  }
  if (status === "UNKNOWN") {
    // CDX-007 FIX: No code evidence found — always MISSING regardless of checked state
    status = "MISSING"
  }
  gaps.push({ criterion: criterion.text, status, section: criterion.section })
}
```

## STEP 4: Check Task Completion Rate

```javascript
const taskStats = extractTaskStats(workSummary)
```

## STEP 4.5: Doc-Consistency Cross-Checks

Non-blocking sub-step: validates that key values (version, agent count, etc.) are consistent across documentation and config files. Reports PASS/DRIFT/SKIP per check. Uses PASS/DRIFT/SKIP (not ADDRESSED/MISSING) to avoid collision with gap-analysis regex counts.

```javascript
// BACK-009: Guard: Only run doc-consistency if WORK phase succeeded and >=50% tasks completed
let docConsistencySection = ""
const consistencyGuardPass =
  checkpoint.phases?.work?.status !== "failed" &&
  taskStats.total > 0 &&
  (taskStats.completed / taskStats.total) >= 0.5

if (consistencyGuardPass) {
  const consistencyTalisman = readTalisman()
  const customChecks = consistencyTalisman?.arc?.consistency?.checks || []

  // Default checks when talisman does not define any
  const DEFAULT_CONSISTENCY_CHECKS = [
    {
      name: "version_sync",
      description: "Plugin version matches across config and docs",
      source: { file: ".claude-plugin/plugin.json", extractor: "json_field", field: "version" },
      targets: [
        { path: "CLAUDE.md", pattern: "version:\\s*[0-9]+\\.[0-9]+\\.[0-9]+" },
        { path: "README.md", pattern: "version:\\s*[0-9]+\\.[0-9]+\\.[0-9]+" }
      ]
    },
    {
      name: "agent_count",
      description: "Review agent count matches across docs",
      source: { file: "agents/review/*.md", extractor: "glob_count" },
      targets: [
        { path: "CLAUDE.md", pattern: "\\d+\\s+agents" },
        { path: ".claude-plugin/plugin.json", pattern: "\"agents\"" }
      ]
    }
  ]

  const checks = customChecks.length > 0 ? customChecks : DEFAULT_CONSISTENCY_CHECKS

  // Security patterns: SAFE_REGEX_PATTERN_CC, SAFE_PATH_PATTERN, SAFE_GLOB_PATH_PATTERN — see security-patterns.md
  // QUAL-003: _CC suffix = "Consistency Check" — narrower than SAFE_REGEX_PATTERN (excludes $, |, parens)
  const SAFE_REGEX_PATTERN_CC = /^[a-zA-Z0-9._\-\/ \\\[\]{}^+?*]+$/
  const SAFE_PATH_PATTERN_CC = /^[a-zA-Z0-9._\-\/]+$/
  const SAFE_GLOB_PATH_PATTERN = /^[a-zA-Z0-9._\-\/*]+$/
  const SAFE_DOT_PATH = /^[a-zA-Z0-9._]+$/
  const VALID_EXTRACTORS = ["glob_count", "regex_capture", "json_field", "line_count"]

  const consistencyResults = []

  for (const check of checks) {
    if (!check.name || !check.source || !Array.isArray(check.targets)) {
      consistencyResults.push({ name: check.name || "unknown", status: "SKIP", reason: "Malformed check definition" })
      continue
    }

    // BACK-005: Normalize empty patterns to undefined
    for (const target of check.targets) {
      if (target.pattern === "") target.pattern = undefined
    }

    // Validate source file path (glob_count allows * in path for shell expansion)
    const pathValidator = check.source.extractor === "glob_count" ? SAFE_GLOB_PATH_PATTERN : SAFE_PATH_PATTERN_CC
    if (!pathValidator.test(check.source.file)) {
      consistencyResults.push({ name: check.name, status: "SKIP", reason: `Unsafe source path: ${check.source.file}` })
      continue
    }
    // SEC-002: Path traversal and absolute path check
    if (check.source.file.includes('..') || check.source.file.startsWith('/')) {
      consistencyResults.push({ name: check.name, status: "SKIP", reason: "Path traversal or absolute path in source" })
      continue
    }
    if (!VALID_EXTRACTORS.includes(check.source.extractor)) {
      consistencyResults.push({ name: check.name, status: "SKIP", reason: `Invalid extractor: ${check.source.extractor}` })
      continue
    }
    if (check.source.extractor === "json_field" && check.source.field && !SAFE_DOT_PATH.test(check.source.field)) {
      consistencyResults.push({ name: check.name, status: "SKIP", reason: `Unsafe field path: ${check.source.field}` })
      continue
    }

    // --- Extract source value ---
    let sourceValue = null
    try {
      if (check.source.extractor === "json_field") {
        // BACK-004: Validate file extension for json_field extractor
        if (!check.source.file.match(/\.(json|jsonc|json5)$/i)) {
          consistencyResults.push({ name: check.name, status: "SKIP", reason: "json_field extractor requires .json file" })
          continue
        }
        const content = Read(check.source.file)
        const parsed = JSON.parse(content)
        const FORBIDDEN_KEYS = new Set(['__proto__', 'constructor', 'prototype'])
        sourceValue = String(check.source.field.split('.').reduce((obj, key) => {
          if (FORBIDDEN_KEYS.has(key)) throw new Error(`Forbidden path key: ${key}`)
          return obj[key]
        }, parsed) ?? "")
      } else if (check.source.extractor === "glob_count") {
        // Intentionally unquoted: glob expansion required. SAFE_GLOB_PATH_PATTERN validated above.
        // CDX-003 FIX: Use -- to prevent glob results starting with - being parsed as flags
        const globResult = Bash(`ls -1 -- ${check.source.file} 2>/dev/null | wc -l`)
        sourceValue = globResult.stdout.trim()
      } else if (check.source.extractor === "line_count") {
        const lcResult = Bash(`wc -l < "${check.source.file}" 2>/dev/null`)
        sourceValue = lcResult.stdout.trim()
      } else if (check.source.extractor === "regex_capture") {
        if (!check.source.pattern || !SAFE_REGEX_PATTERN_CC.test(check.source.pattern)) {
          consistencyResults.push({ name: check.name, status: "SKIP", reason: "Unsafe source regex" })
          continue
        }
        const rgResult = Bash(`rg --no-messages -o "${check.source.pattern}" "${check.source.file}" | head -1`)
        sourceValue = rgResult.stdout.trim()
      } else {
        consistencyResults.push({ name: check.name, status: "SKIP", reason: `Unknown extractor: ${check.source.extractor}` })
        continue
      }
    } catch (extractErr) {
      consistencyResults.push({ name: check.name, status: "SKIP", reason: `Source extraction failed: ${extractErr.message}` })
      continue
    }

    if (!sourceValue || sourceValue.length === 0) {
      consistencyResults.push({ name: check.name, status: "SKIP", reason: "Source value empty or not found" })
      continue
    }

    // --- Compare against each target ---
    for (const target of check.targets) {
      if (!target.path || !SAFE_PATH_PATTERN_CC.test(target.path)) {
        consistencyResults.push({ name: `${check.name}->${target.path || "unknown"}`, status: "SKIP", reason: "Unsafe target path" })
        continue
      }
      if (target.pattern && !SAFE_REGEX_PATTERN_CC.test(target.pattern)) {
        consistencyResults.push({ name: `${check.name}->${target.path}`, status: "SKIP", reason: "Unsafe target pattern" })
        continue
      }

      let targetStatus = "SKIP"
      try {
        if (target.pattern) {
          // SEC-001: Use -- separator and shell escape the pattern
          // SEC-003: Cap pattern length to prevent excessively long Bash commands
          if (target.pattern.length > 500) {
            consistencyResults.push({ name: `${check.name}->${target.path}`, status: "SKIP", reason: "Pattern exceeds 500 char limit" })
            continue
          }
          const escapedPattern = target.pattern.replace(/["$\`\\]/g, '\\$&')
          const targetResult = Bash(`rg --no-messages -o -- "${escapedPattern}" "${target.path}" 2>/dev/null | head -1`)
          const targetValue = targetResult.stdout.trim()
          if (targetValue.length === 0) {
            targetStatus = "DRIFT"
          } else if (targetValue.includes(sourceValue)) {
            targetStatus = "PASS"
          } else {
            targetStatus = "DRIFT"
          }
        } else {
          // CDX-001 FIX: Escape sourceValue to prevent shell injection
          const escapedSourceValue = sourceValue.replace(/["$`\\]/g, '\\$&')
          const grepResult = Bash(`rg --no-messages --fixed-strings -l -- "${escapedSourceValue}" "${target.path}" 2>/dev/null`)
          targetStatus = grepResult.stdout.trim().length > 0 ? "PASS" : "DRIFT"
        }
      } catch (targetErr) {
        targetStatus = "SKIP"
      }

      consistencyResults.push({
        name: `${check.name}->${target.path}`,
        status: targetStatus,
        sourceValue,
        reason: targetStatus === "DRIFT" ? `Source value "${sourceValue}" not matched in ${target.path}` : undefined
      })
    }
  }

  // --- Build doc-consistency report section ---
  // BACK-007: Cap at 100 results
  const MAX_CONSISTENCY_RESULTS = 100
  const displayResults = consistencyResults.length > MAX_CONSISTENCY_RESULTS
    ? consistencyResults.slice(0, MAX_CONSISTENCY_RESULTS)
    : consistencyResults

  const passCount = consistencyResults.filter(r => r.status === "PASS").length
  const driftCount = consistencyResults.filter(r => r.status === "DRIFT").length
  const skipCount = consistencyResults.filter(r => r.status === "SKIP").length
  const overallStatus = driftCount > 0 ? "WARN" : "PASS"

  docConsistencySection = `\n## DOC-CONSISTENCY\n\n` +
    `**Status**: ${overallStatus}\n` +
    `**Issues**: ${driftCount}\n` +
    `**Checked at**: ${new Date().toISOString()}\n` +
    (consistencyResults.length > MAX_CONSISTENCY_RESULTS ? `**Note**: Showing first ${MAX_CONSISTENCY_RESULTS} of ${consistencyResults.length} results\n` : '') +
    `\n| Check | Status | Detail |\n|-------|--------|--------|\n` +
    displayResults.map(r =>
      `| ${r.name} | ${r.status} | ${r.reason || "---"} |`
    ).join('\n') + '\n\n' +
    `Summary: ${passCount} PASS, ${driftCount} DRIFT, ${skipCount} SKIP\n`

  if (driftCount > 0) {
    warn(`Doc-consistency: ${driftCount} drift(s) detected`)
  }
} else {
  docConsistencySection = `\n## DOC-CONSISTENCY\n\n` +
    `**Status**: SKIP\n` +
    `**Reason**: Guard not met (Phase 5 failed or <50% tasks completed)\n` +
    `**Checked at**: ${new Date().toISOString()}\n`
}
```

## STEP 4.7: Plan Section Coverage

Cross-reference plan H2 headings against committed code changes.

```javascript
let planSectionCoverageSection = ""

if (diffFiles.length === 0) {
  planSectionCoverageSection = `\n## PLAN SECTION COVERAGE\n\n` +
    `**Status**: SKIP\n**Reason**: No files committed during work phase\n`
} else {
  const planContent = Read(enrichedPlanPath)
  const strippedContent = planContent.replace(/```[\s\S]*?```/g, '')
  const planSections = strippedContent.split(/^## /m).slice(1)

  const sectionCoverage = []
  for (const section of planSections) {
    const heading = section.split('\n')[0].trim()

    const skipSections = ['Overview', 'Problem Statement', 'Dependencies',
      'Risk Analysis', 'References', 'Success Metrics', 'Cross-File Consistency',
      'Documentation Impact', 'Documentation Plan', 'Future Considerations',
      'AI-Era Considerations', 'Alternative Approaches', 'Forge Enrichment']
    if (skipSections.some(s => heading.includes(s))) continue

    // Extract identifiers from section text
    const backtickIds = (section.match(/`([a-zA-Z0-9._\-\/]+)`/g) || []).map(m => m.replace(/`/g, ''))
    const filePaths = section.match(/[a-zA-Z0-9_\-\/]+\.(py|ts|js|rs|go|md|yml|json)/g) || []
    const caseNames = (section.match(/\b[A-Z][a-zA-Z0-9]+\b/g) || [])
    const stopwords = new Set(['Create', 'Add', 'Update', 'Fix', 'Implement', 'Section', 'Phase', 'Check', 'Remove', 'Delete'])
    const identifiers = [...new Set([...filePaths, ...backtickIds, ...caseNames])]
      .filter(id => id.length >= 4 && id.length <= 100 && !stopwords.has(id))
      .filter(id => !/^\d+\.\d+(\.\d+)?$/.test(id))
      .slice(0, 20)

    const safeDiffFiles = diffFiles.filter(f => /^[a-zA-Z0-9._\-\/]+$/.test(f) && !f.includes('..'))

    let status = "MISSING"
    for (const id of identifiers) {
      if (!/^[a-zA-Z0-9._\-\/]+$/.test(id)) continue
      if (safeDiffFiles.length === 0) break
      const grepResult = Bash(`rg -l --max-count 1 -- "${id}" ${safeDiffFiles.map(f => `"${f}"`).join(' ')} 2>/dev/null`)
      if (grepResult.stdout.trim().length > 0) {
        status = "ADDRESSED"
        break
      }
    }
    sectionCoverage.push({ heading, status })
  }

  // Check Documentation Impact items (if present)
  const docImpactSection = planSections.find(s => s.startsWith('Documentation Impact'))
  if (docImpactSection) {
    const impactItems = docImpactSection.match(/- \[[ x]\] .+/g) || []
    for (const item of impactItems) {
      const checked = item.startsWith('- [x]')
      const filePath = item.match(/([a-zA-Z0-9._\-\/]+\.(md|json|yml|yaml))/)?.[1]
      if (filePath && diffFiles.includes(filePath)) {
        sectionCoverage.push({ heading: `Doc Impact: ${filePath}`, status: "ADDRESSED" })
      } else if (filePath) {
        sectionCoverage.push({ heading: `Doc Impact: ${filePath}`, status: checked ? "CLAIMED" : "MISSING" })
      }
    }
  }

  const covAddressed = sectionCoverage.filter(s => s.status === "ADDRESSED").length
  const covMissing = sectionCoverage.filter(s => s.status === "MISSING").length
  const covClaimed = sectionCoverage.filter(s => s.status === "CLAIMED").length

  planSectionCoverageSection = `\n## PLAN SECTION COVERAGE\n\n` +
    `**Status**: ${covMissing > 0 ? "WARN" : "PASS"}\n` +
    `**Checked at**: ${new Date().toISOString()}\n\n` +
    `| Section | Status |\n|---------|--------|\n` +
    sectionCoverage.map(s => `| ${s.heading} | ${s.status} |`).join('\n') + '\n\n' +
    `Summary: ${covAddressed} ADDRESSED, ${covMissing} MISSING, ${covClaimed} CLAIMED\n`

  if (covMissing > 0) {
    warn(`Plan section coverage: ${covMissing} MISSING section(s)`)
  }
}
```

## STEP 4.8: Check Evaluator Quality Metrics

Non-blocking sub-step: runs lightweight, evaluator-equivalent quality checks on committed code. Zero LLM cost — uses shell commands and AST analysis only. Score calculations are approximations and may differ from the E2E evaluator's exact algorithm.

```javascript
let evaluatorMetricsSection = ""

// Guard: verify python3 is available
const pythonCheck = Bash(`command -v python3 2>/dev/null`).stdout.trim()
if (!pythonCheck) {
  evaluatorMetricsSection = `\n## EVALUATOR QUALITY METRICS\n\n**Status**: SKIP\n**Reason**: python3 not found in PATH\n`
} else {
  // BACK-206 FIX: Exclude evaluation/ test files and remove redundant ./.* exclusion
  const pyFilesRaw = Bash(`find . -name "*.py" -not -path "./.venv/*" -not -path "./__pycache__/*" -not -path "./.tox/*" -not -path "./.pytest_cache/*" -not -path "./build/*" -not -path "./dist/*" -not -path "./.eggs/*" -not -path "./evaluation/*" -not -name "test_*.py" -not -name "*_test.py" | head -200`)
    .stdout.trim().split('\n').filter(f => f.length > 0)

  // SEC: Filter file paths through SAFE_PATH_PATTERN_CC before passing to heredoc.
  // CRITICAL: This regex MUST remain strict (alphanumeric + ._-/ only). Weakening it
  // would allow shell metacharacters ($, `, ;, etc.) to reach the heredoc interpolation
  // on the Bash() call below, enabling command injection via crafted filenames.
  const pyFiles = pyFilesRaw.filter(f => /^[a-zA-Z0-9._\-\/]+$/.test(f) && !f.includes('..') && !f.startsWith('/'))

  if (pyFiles.length === 0) {
    evaluatorMetricsSection = `\n## EVALUATOR QUALITY METRICS\n\n**Status**: SKIP\n**Reason**: No Python files found\n`
  } else {
    // 1. Docstring coverage + 2. Function length audit (combined single-pass)
    // SEC-002 FIX: Write file list to temp file instead of heredoc to prevent shell interpretation
    const pyFileListPath = `/tmp/rune-pyfiles-${Date.now()}.txt`
    Write(pyFileListPath, pyFiles.join('\n'))
    const astResult = Bash(`python3 -c "
import ast, sys
from pathlib import Path
total = with_doc = long_count = skipped = 0
long_fns = []
for f in sys.stdin.read().strip().split('\\n'):
    try:
        tree = ast.parse(Path(f).read_text(encoding='utf-8', errors='ignore'))
    except (SyntaxError, UnicodeDecodeError, OSError):
        skipped += 1
        continue
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            total += 1
            if ast.get_docstring(n): with_doc += 1
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if n.end_lineno and (n.end_lineno - n.lineno) > 40:
                long_count += 1
                long_fns.append(f'{f}:{n.lineno} {n.name} ({n.end_lineno - n.lineno} lines)')
print(f'{with_doc}/{total}/{long_count}/{skipped}')
for fn in long_fns[:10]: print(fn)
" < "${pyFileListPath}"`)
    Bash(`rm -f "${pyFileListPath}"`)  // cleanup temp file
    const parts = astResult.stdout.trim().split('\n')
    const [withDoc, totalDefs, longCount, skippedFiles] = parts[0].split('/').map(Number)
    const longFunctions = parts.slice(1)
    const docPct = totalDefs > 0 ? Math.round((withDoc / totalDefs) * 100) : 0
    const docScore = totalDefs > 0 ? ((withDoc / totalDefs) * 10).toFixed(1) : "N/A"
    const docStatus = docPct >= 80 ? "PASS" : docPct >= 50 ? "WARN" : "FAIL"
    const structScore = Math.max(0, 10 - longCount * 1.0).toFixed(1)
    const structStatus = longCount === 0 ? "PASS" : longCount <= 2 ? "WARN" : "FAIL"

    // 3. Evaluation test pass rate
    let evalStatus = "SKIP"
    let evalDetail = "No evaluation/ directory"
    // SEC-005 FIX: Guard against symlink traversal on evaluation/ path
    const evalIsSymlink = Bash(`test -L evaluation && echo "yes" || echo "no"`).stdout.trim()
    if (evalIsSymlink === "yes") {
      evalDetail = "evaluation/ is a symlink — skipped for safety"
    }
    const evalExists = evalIsSymlink !== "yes"
      ? Bash(`find evaluation -maxdepth 1 -name "*.py" -type f 2>/dev/null | wc -l`).stdout.trim()
      : "0"
    if (parseInt(evalExists) > 0) {
      // BACK-202 FIX: Capture exit code before piping to avoid tail masking pytest status
      const evalResult = Bash(`timeout 30s python -m pytest evaluation/ -v --tb=line 2>&1 > /tmp/rune-eval-out.txt; echo $?`)
      const evalRc = parseInt(evalResult.stdout.trim())
      const evalOutput = Bash(`tail -20 /tmp/rune-eval-out.txt`).stdout.trim()
      Bash(`rm -f /tmp/rune-eval-out.txt`)
      const output = evalOutput
      // Parse pass/fail counts from pytest summary
      const summaryMatch = output.match(/(\d+) passed(?:, (\d+) failed)?/)
      const passed = summaryMatch ? parseInt(summaryMatch[1]) : 0
      const failed = summaryMatch ? parseInt(summaryMatch[2] || '0') : 0
      if (evalRc === 0) {
        evalStatus = "PASS"
        evalDetail = summaryMatch ? `${passed} passed` : "all tests passed"
      } else if (evalRc === 5) {
        evalStatus = "SKIP"
        evalDetail = "No tests collected (exit code 5)"
      } else {
        evalStatus = "FAIL"
        evalDetail = summaryMatch ? `${passed} passed, ${failed} failed` : output.split('\n').pop() || "unknown"
      }
    }

    evaluatorMetricsSection = `\n## EVALUATOR QUALITY METRICS\n\n` +
      `**Checked at**: ${new Date().toISOString()}\n\n` +
      `| Metric | Status | Score | Detail |\n|--------|--------|-------|--------|\n` +
      `| Docstring coverage | ${docStatus} | ${docScore}/10 | ${withDoc}/${totalDefs} definitions (${docPct}%)${skippedFiles > 0 ? `, ${skippedFiles} files skipped` : ''} |\n` +
      `| Function length | ${structStatus} | ${structScore}/10 | ${longCount} functions over 40 lines |\n` +
      `| Evaluation tests | ${evalStatus} | — | ${evalDetail} |\n` +
      (longFunctions.length > 0 ? `\n**Long functions**:\n${longFunctions.map(f => '- ' + f).join('\n')}\n` : '') +
      '\n'
  }
}
```

## STEP 5: Write Gap Analysis Report

```javascript
const addressed = gaps.filter(g => g.status === "ADDRESSED").length
const partial = gaps.filter(g => g.status === "PARTIAL").length
const missing = gaps.filter(g => g.status === "MISSING").length

const report = `# Implementation Gap Analysis\n\n` +
  `**Plan**: ${checkpoint.plan_file}\n` +
  `**Date**: ${new Date().toISOString()}\n` +
  `**Criteria found**: ${criteria.length}\n\n` +
  `## Summary\n\n` +
  `| Status | Count |\n|--------|-------|\n` +
  `| ADDRESSED | ${addressed} |\n| PARTIAL | ${partial} |\n| MISSING | ${missing} |\n\n` +
  (missing > 0 ? `## MISSING (not found in committed code)\n\n` +
    gaps.filter(g => g.status === "MISSING").map(g =>
      `- [ ] ${g.criterion} (from section: ${g.section})`
    ).join('\n') + '\n\n' : '') +
  (partial > 0 ? `## PARTIAL (some evidence, not fully addressed)\n\n` +
    gaps.filter(g => g.status === "PARTIAL").map(g =>
      `- [ ] ${g.criterion} (from section: ${g.section})`
    ).join('\n') + '\n\n' : '') +
  `## ADDRESSED\n\n` +
  gaps.filter(g => g.status === "ADDRESSED").map(g =>
    `- [x] ${g.criterion}`
  ).join('\n') + '\n\n' +
  `## Task Completion\n\n` +
  `- Completed: ${taskStats.completed}/${taskStats.total} tasks\n` +
  `- Failed: ${taskStats.failed} tasks\n` +
  docConsistencySection +
  planSectionCoverageSection +
  evaluatorMetricsSection

Write(`tmp/arc/${id}/gap-analysis.md`, report)

updateCheckpoint({
  phase: "gap_analysis",
  status: "completed",
  artifact: `tmp/arc/${id}/gap-analysis.md`,
  artifact_hash: sha256(report),
  phase_sequence: 5.5,
  team_name: null
})
```

**Output**: `tmp/arc/{id}/gap-analysis.md`

**Failure policy**: Non-blocking (WARN). Gap analysis is advisory -- missing criteria are flagged but do not halt the pipeline. The report is available as context for Phase 6 (CODE REVIEW).
