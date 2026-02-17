# Chunk Scoring — File Complexity Engine

> Scores files by complexity and groups them into balanced chunks for chunked review.
> Used when `changed_files.length > CHUNK_THRESHOLD` to partition work across multiple Roundtable Circle passes.

## Constants

```javascript
const CHUNK_THRESHOLD   = 20   // Files above this trigger chunking (configurable: rune-gaze.chunk_threshold)
const CHUNK_TARGET_SIZE = 15   // Target files per chunk (configurable: rune-gaze.chunk_target_size)
const MAX_CHUNKS        = 5    // Circuit breaker — prevents runaway review loops (configurable: rune-gaze.max_chunks)
const MIN_ASH_BUDGET    = 20   // Ward Sentinel's cap — no chunk should exceed this
```

## File Type Weights

```javascript
const TYPE_WEIGHTS = {
  // Dynamic typing → higher review complexity
  py: 1.5, rb: 1.5, js: 1.5,
  // Static types reduce review burden
  go: 1.0, java: 1.0, ts: 1.0, rs: 1.2,
  // UI components add complexity
  tsx: 1.3, jsx: 1.5,
  // DB and shell are error-prone
  sql: 1.5, sh: 1.3,
  // Docs are lower complexity
  md: 0.5, txt: 0.3,
}
```

## Security-Critical Patterns

```javascript
// Files matching these patterns are pinned as read-only context in EVERY chunk,
// even if assigned to a different chunk. Ward Sentinel can cross-reference auth
// context across all chunk reviews.
const SECURITY_CRITICAL_PATTERNS = [
  '**/auth/**', '**/middleware/auth*', '**/security/**',
  '**/validators/**', '**/*permission*', '**/crypto/**',
  '**/payment/**', '**/migrate/**', '**/migration*',
]
```

## `scoreFile(file, diffStats)`

**Inputs**:
- `file` — string: relative file path
- `diffStats` — `{ [file]: { insertions, deletions, status } }` from `git diff --numstat`

**Outputs**: `{ file, complexity, type, riskFactor, ext }`

**Error handling**: Missing `diffStats[file]` defaults to `linesChanged = 1` (not 0 — prevents zero-complexity invisibility). Missing file on disk → complexity = 1.0.

```javascript
function scoreFile(file, diffStats) {
  const stat = diffStats[file]
  // CRITICAL: Math.max floor prevents zero-complexity for renamed/permission-changed files
  const linesChanged = Math.max(
    (stat?.insertions ?? 0) + (stat?.deletions ?? 0),
    1
  )
  // Fallback: wc -l for untracked files not in diffStats
  const effectiveLines = stat ? linesChanged : (wcLines(file) || 1)

  const sizeFactor = Math.min(effectiveLines / 50, 3.0)
  const typeFactor = TYPE_WEIGHTS[ext(file)] ?? 1.0

  let riskFactor = 1.0
  if (matchesAnyPattern(file, SECURITY_CRITICAL_PATTERNS)) riskFactor = 2.0
  if (stat?.status === 'A') riskFactor *= 1.5   // New file — no history, higher review risk
  if (isTestFile(file))     riskFactor *= 0.5   // Tests lower relative risk

  const complexity = sizeFactor * typeFactor * riskFactor
  const type = classify(file)  // 'code' | 'docs' | 'skip' | 'critical_deletion'

  return { file, complexity, type, riskFactor, ext: ext(file) }
}
```

## `groupByDirectory(scoredFiles)`

**Inputs**: `scoredFiles` — `{ file, complexity, type, riskFactor }[]`

**Outputs**: `{ dir, files, totalComplexity }[]` — one entry per unique parent directory

**Error handling**: Root-level files (no `/` in path) use `<root>` sentinel directory. Empty input returns `[]`.

```javascript
function groupByDirectory(scoredFiles) {
  if (scoredFiles.length === 0) return []

  const dirMap = new Map()  // dir → { files: [], totalComplexity: 0 }

  for (const scored of scoredFiles) {
    const lastSlash = scored.file.lastIndexOf('/')
    // Files like 'README.md' or 'Dockerfile' at repo root → '<root>' sentinel
    const dir = lastSlash >= 0 ? scored.file.slice(0, lastSlash) : '<root>'

    if (!dirMap.has(dir)) {
      dirMap.set(dir, { dir, files: [], totalComplexity: 0 })
    }
    const group = dirMap.get(dir)
    group.files.push(scored)
    group.totalComplexity += scored.complexity
  }

  return Array.from(dirMap.values())
}
```

## `avgComplexity(scoredFiles)`

**Inputs**: `scoredFiles` — `{ complexity }[]`

**Outputs**: `number` — mean complexity across all files

**Error handling**: Empty array returns `1.0` (safe default; prevents NaN in bin-packing calculation).

```javascript
function avgComplexity(scoredFiles) {
  if (scoredFiles.length === 0) return 1.0
  return scoredFiles.reduce((sum, f) => sum + f.complexity, 0) / scoredFiles.length
}
```

## `splitChunk(chunk, maxSize)`

**Inputs**:
- `chunk` — `{ files, totalComplexity, chunkIndex }` — oversized chunk to split
- `maxSize` — `number` — max files per sub-chunk (defaults to `MIN_ASH_BUDGET`)

**Outputs**: `{ files, totalComplexity, chunkIndex }[]` — two or more balanced sub-chunks

**Error handling**: Single-file chunk returns it unchanged. Empty chunk returns `[]`.

```javascript
function splitChunk(chunk, maxSize = MIN_ASH_BUDGET) {
  if (chunk.files.length <= maxSize) return [chunk]
  if (chunk.files.length === 0) return []

  // Sort by complexity descending — interleave high/low for balance
  const sorted = [...chunk.files].sort((a, b) => b.complexity - a.complexity)
  const subChunks = []
  let current = { files: [], totalComplexity: 0, chunkIndex: chunk.chunkIndex }

  for (const scored of sorted) {
    if (current.files.length >= maxSize) {
      subChunks.push(current)
      current = { files: [], totalComplexity: 0, chunkIndex: chunk.chunkIndex }
    }
    current.files.push(scored)
    current.totalComplexity += scored.complexity
  }
  if (current.files.length > 0) subChunks.push(current)

  return subChunks
}
```

## `groupIntoChunks(scoredFiles, targetSize)`

**Inputs**:
- `scoredFiles` — scored file array (output of `scoreFile` mapped across changed files)
- `targetSize` — `number` default `CHUNK_TARGET_SIZE`

**Outputs**: `{ files, totalComplexity, chunkIndex }[]` — balanced, directory-aware chunks

**Error handling**: Chunks exceeding `MAX_CHUNKS` are redistributed into larger chunks (not silently dropped). Files in excess are logged to Coverage Gaps in TOME.

```javascript
function groupIntoChunks(scoredFiles, targetSize = CHUNK_TARGET_SIZE) {
  // 1. Group by parent directory (preserves cross-file context)
  const dirGroups = groupByDirectory(scoredFiles)

  // 2. Sort directories by total complexity — highest first (first-fit decreasing)
  dirGroups.sort((a, b) => b.totalComplexity - a.totalComplexity)

  // 3. Bin-pack directories into chunks
  const avg = avgComplexity(scoredFiles)
  const maxChunkComplexity = targetSize * avg
  const chunks = []

  for (const group of dirGroups) {
    // Try to fit this directory into an existing chunk
    const target = chunks.find(c =>
      c.files.length + group.files.length <= targetSize &&
      c.totalComplexity + group.totalComplexity <= maxChunkComplexity
    )
    if (target) {
      target.files.push(...group.files)
      target.totalComplexity += group.totalComplexity
    } else {
      chunks.push({
        files: [...group.files],
        totalComplexity: group.totalComplexity,
        chunkIndex: chunks.length,
      })
    }
  }

  // 4. Split any chunk that exceeds MIN_ASH_BUDGET
  const splitChunks = chunks.flatMap(chunk =>
    chunk.files.length > MIN_ASH_BUDGET ? splitChunk(chunk) : [chunk]
  )

  // 5. Re-index after split (chunkIndex must be sequential, 0-based)
  splitChunks.forEach((c, i) => { c.chunkIndex = i })

  // 6. Circuit breaker — MAX_CHUNKS hard cap
  if (splitChunks.length > MAX_CHUNKS) {
    const dropped = splitChunks.slice(MAX_CHUNKS)
    const droppedFiles = dropped.flatMap(c => c.files.map(f => f.file))
    warn(`Chunk count ${splitChunks.length} exceeds MAX_CHUNKS=${MAX_CHUNKS}. Redistributing ${droppedFiles.length} files into larger chunks.`)

    // Redistribute excess files back into the last allowed chunk
    // (not silently dropped — they become Coverage Gaps if still oversized)
    const lastChunk = splitChunks[MAX_CHUNKS - 1]
    lastChunk.files.push(...dropped.flatMap(c => c.files))
    lastChunk.totalComplexity += dropped.reduce((s, c) => s + c.totalComplexity, 0)

    // Log files that pushed beyond MIN_ASH_BUDGET as Coverage Gaps
    if (lastChunk.files.length > MIN_ASH_BUDGET) {
      const gapFiles = lastChunk.files.slice(MIN_ASH_BUDGET).map(f => f.file)
      warn(`Coverage Gaps (beyond MAX_CHUNKS capacity): ${gapFiles.join(', ')}`)
    }

    return splitChunks.slice(0, MAX_CHUNKS)
  }

  return splitChunks
}
```

## Security Pinning

After `groupIntoChunks()`, collect security-critical files that must appear in every chunk as read-only context:

```javascript
function collectSecurityPins(scoredFiles) {
  return scoredFiles
    .filter(f => matchesAnyPattern(f.file, SECURITY_CRITICAL_PATTERNS))
    .map(f => f.file)
}

// Usage in chunk orchestrator:
// const securityPins = collectSecurityPins(scoredFiles)
// Each chunk review receives: { files: chunk.files, contextFiles: securityPins }
// contextFiles are read-only — Ashes can reference them but they don't count toward chunk budget
```

## References

- [Smart Selection](smart-selection.md) — Ash budget enforcement and file classification
- [Chunk Orchestrator](chunk-orchestrator.md) — How chunks are reviewed and merged
- [Security Patterns](../../rune-orchestration/references/security-patterns.md) — SAFE_PATH_PATTERN and validation
- [Team Lifecycle Guard](../../rune-orchestration/references/team-lifecycle-guard.md) — Pre-create guard pattern
