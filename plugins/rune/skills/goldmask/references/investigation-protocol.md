# Investigation Protocol — 5-Step for Impact Tracers

Each Impact tracer follows this protocol to find dependencies within its assigned layer.

## Step 1: SCOPE

Read the changed files list from the inscription contract.

```
Input: changed_files[] from inscription.json
Output: filtered list of files relevant to THIS tracer's layer
```

Filter by layer:
- **Data tracer**: models, migrations, schemas, serializers
- **API tracer**: routes, controllers, endpoints, middleware
- **Business tracer**: services, domain, validators, state machines
- **Event tracer**: events, handlers, consumers, producers, jobs
- **Config tracer**: config files, env reads, CI/CD, Dockerfiles

If no files match this layer, report "No changes in {layer} layer" and exit.

## Step 2: IDENTIFY

Find symbols/types/functions **defined** in the changed files.

```bash
# For each changed file in scope:
# 1. Read the file
# 2. Extract exported symbols:
#    - Function/method definitions
#    - Class/type definitions
#    - Exported constants
#    - Interface/protocol definitions
```

Use layer-specific patterns from `trace-patterns.md`. Record each symbol with its file and line number.

## Step 3: TRACE

For each identified symbol, grep for usages across the codebase.

```bash
# Direct usages (Method A — confidence 0.80):
grep -rn "{symbol_name}" --include="*.{ext}" .

# Type references (Method B — confidence 0.60):
grep -rn "{type_name}" --include="*.{ext}" .

# Co-change evidence (Method C — confidence 0.40/0.60):
# Check risk-map.json if available for co-change edges
```

**Important**: Exclude the changed files themselves from results. Only report **other** files that depend on the changed symbols.

Filter out false positives:
- String literals containing the symbol name (comments, docs)
- Variable names that happen to match
- Test mocks/stubs (report separately)

## Step 4: ASSESS

For each dependency found, classify using confidence thresholds:

| Classification | Confidence | Evidence Required |
|---------------|------------|-------------------|
| MUST-CHANGE | >= 0.80 | At least Method A signal (direct import/call) |
| SHOULD-CHECK | >= 0.50 | Method B signal (type reference) or multiple Method C signals |
| MAY-AFFECT | >= 0.20 | Single Method C signal or weak indirect reference |

When multiple methods apply, combine with Noisy-OR:
```
combined = 1 - (1 - c_A) * (1 - c_B) * (1 - c_C)
```

## Step 5: REPORT

Write structured output to `{output_dir}/{layer}-layer.md`:

```markdown
# {Layer} Layer Impact Report

**Tracer**: {layer}-layer-tracer
**Changed files in scope**: {N}
**Dependencies found**: {N}

## Findings

### {LAYER}-{NNN} [{CLASSIFICATION}] (confidence: {score})

**Changed symbol**: `{symbol}` in `{changed_file}:{line}`
**Impacted file**: `{dependent_file}:{line}`
**Evidence**:
- Method A: {description of direct import/call}
- Method B: {description of type reference}
- Method C: {co-change data if available}

**Propagation chain**: {file1} -> {file2} -> {file3}

---
```

### Finding ID Convention

Format: `{LAYER}-{NNN}` where LAYER is (tracers use these prefixes; coordinator maps to `GOLD-NNN` in final output):
- `DATA` — Data Layer
- `API` — API Contract
- `BIZ` — Business Logic
- `EVT` — Event/Message
- `CFG` — Config/Dependency

### Transitive Depth

Track propagation chains up to depth 3:
- Depth 1: A imports B (direct)
- Depth 2: A imports B, B imports C (one hop)
- Depth 3: A -> B -> C -> D (two hops, maximum)

Do NOT trace beyond depth 3 — diminishing returns and noise.
