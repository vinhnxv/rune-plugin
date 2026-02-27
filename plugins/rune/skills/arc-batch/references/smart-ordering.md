# Smart Plan Ordering — Tier 1 Algorithm

Phase 1.5 reorders the `planPaths` array in memory to reduce merge conflicts and version collisions when running multiple plans in batch. Executes after Phase 1 (pre-flight validation), before Phase 2 (dry run).

## Activation Conditions

Smart ordering activates only when explicitly selected. The decision tree:

### CLI Flags (highest priority)
- `--no-smart-sort` → Skip all ordering (preserve raw order)
- `--smart-sort` → Force smart ordering (even on queue files)
- Conflicting (`--smart-sort` + `--no-smart-sort`) → `--no-smart-sort` wins (warn user)

### Resume Guard (before talisman)
- `--resume` mode → Skip (preserve partial batch order)

### Talisman Mode (second priority)
- `arc.batch.smart_ordering.enabled: false` → Skip all ordering
- `arc.batch.smart_ordering.mode: "off"` → Skip all ordering
- `arc.batch.smart_ordering.mode: "auto"` → Auto-apply (pre-v1.118.0 default behavior)

### Input-Type Heuristic (default, mode="ask")
- Queue file (`.txt`) → Skip (respect user's explicit order)
- Glob pattern → AskUserQuestion with 3 options:
  1. Smart ordering (Recommended)
  2. Alphabetical
  3. As discovered (glob default)

### Always Skip
- `planPaths.length <= 1` (nothing to reorder)

### Note on `enabled` vs `mode: "off"`
Both achieve identical behavior (skip ordering). `enabled: false` is the master kill switch with absolute precedence. `mode: "off"` is the preferred path for new configurations.

## Algorithm

### Step 1: Extract File Targets

For each plan, extract the set of files it will modify:

1. Parse YAML frontmatter for `scope` or `files_modified` field
2. If no frontmatter field, grep plan content for backtick-wrapped file paths (`` `path/to/file.ext` ``)
3. Normalize paths: strip leading `./`, collapse duplicates

### Step 2: Build Overlap Map

For each pair of plans, check if their file target sets intersect.

**Universal exclusion list** — these files are excluded from overlap detection because nearly every plan touches them:
- `plugin.json` (and `.claude-plugin/plugin.json`)
- `CHANGELOG.md`
- `CLAUDE.md`
- `marketplace.json` (and `.claude-plugin/marketplace.json`)
- `README.md`

After excluding universal files, if two plans share any remaining file targets, they have overlap.

### Step 3: Classify Plans

For each plan:
- `is_isolated = true` if the plan has NO file overlap with any other plan (after universal exclusions)
- `is_isolated = false` if it shares at least one non-universal file target with another plan

### Step 4: Extract Version Target

Read `version_target` from each plan's YAML frontmatter.
- Present: parse as semver string (e.g., `"1.99.0"`)
- Missing: treat as `null` (sorted last)

### Step 5: Sort

Stable sort with composite key `(is_isolated DESC, version_target ASC, filename ASC)`:

1. **Isolated plans first** (`is_isolated = true` before `false`)
   - Isolated plans have zero risk of merge conflicts — run them first
2. **Lower version_target first** (`null` sorts last)
   - Plans targeting `1.98.0` run before plans targeting `1.99.0`
   - This respects version ordering and reduces version bump collisions
3. **Alphabetical filename tiebreaker** for deterministic ordering

### Step 6: Replace planPaths (Memory Only)

Replace the `planPaths` array with the sorted result. This is a memory-only operation — no files are written in Phase 1.5. Phase 5 writes `plan-list.txt` from the already-reordered array.

### Step 7: Log Summary

Log the reordering results:
- Number of isolated vs. conflicting plans
- New execution order (numbered list)
- Any plans with missing version_target (informational warning)

## Interaction with Shard Grouping

Phase 0 (shard auto-sorting) runs FIRST on its subset. Phase 1.5 (smart ordering) runs SECOND on the full plan list. This means:

- Smart ordering applies to all plans (both regular and shard plans)
- Shard grouping then re-groups shard plans within their feature groups
- `--no-smart-sort` disables smart ordering; shard grouping is independent (`--no-shard-sort`)
- Both can be disabled simultaneously for raw glob/queue order

## Flag Coexistence

| `--smart-sort` | `--no-smart-sort` | `--no-shard-sort` | Result |
|----------------|-------------------|-------------------|--------|
| false | false | false | Input-type detection + shard grouping (default) |
| false | true | false | Raw order, shard grouping still active |
| true | false | false | Force smart ordering + shard grouping |
| true | true | false | Conflicting — `--no-smart-sort` wins (warn user) |
| false | false | true | Input-type detection, no shard grouping |
| true | false | true | Force smart ordering, no shard grouping |
| false | true | true | Raw glob/queue order preserved |
| true | true | true | Conflicting — `--no-smart-sort` wins (warn user) |

## Limitations (Tier 1)

- **File-level granularity only**: Two plans modifying different functions in the same file are treated as conflicting
- **No dependency inference**: Does not detect producer/consumer relationships beyond file overlap
- **No weighted scoring**: All overlap is binary (overlap or not) — no severity weighting
- **Frontmatter-dependent**: Plans without `version_target` or `scope`/`files_modified` get less accurate classification
- **No conflict clustering**: Overlapping plans are not grouped into conflict clusters for optimal interleaving

These limitations are documented as future work for Tier 2+ implementations.
