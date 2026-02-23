---
name: audit
description: |
  Full codebase audit using Agent Teams. Sets scope=full and depth=deep (by default),
  then delegates to the shared Roundtable Circle orchestration phases.
  Summons up to 7 built-in Ashes (plus custom from talisman.yml). Optional `--deep`
  runs multi-wave investigation with deep Ashes. Supports `--focus` for targeted audits.

  <example>
  user: "/rune:audit"
  assistant: "The Tarnished convenes the Roundtable Circle for audit..."
  </example>
user-invocable: true
disable-model-invocation: false
argument-hint: "[--deep] [--focus <area>] [--max-agents <N>] [--dry-run] [--no-lore] [--deep-lore] [--standard] [--todos-dir <path>]"
allowed-tools:
  - Task
  - TaskCreate
  - TaskList
  - TaskUpdate
  - TaskGet
  - TeamCreate
  - TeamDelete
  - SendMessage
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

**Runtime context** (preprocessor snapshot):
- Active workflows: !`ls tmp/.rune-*-*.json 2>/dev/null | grep -c '"active"' || echo 0`
- Current branch: !`git branch --show-current 2>/dev/null || echo "n/a"`

# /rune:audit — Full Codebase Audit

Thin wrapper that sets audit-specific parameters, then delegates to the shared Roundtable Circle orchestration. Unlike `/rune:appraise` (which reviews changed files via git diff), `/rune:audit` scans the entire project.

**Load skills**: `roundtable-circle`, `context-weaving`, `rune-echoes`, `rune-orchestration`, `codex-cli`, `polling-guard`, `zsh-compat`

## Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--focus <area>` | Limit audit to specific area: `security`, `performance`, `quality`, `frontend`, `docs`, `backend`, `full` | `full` |
| `--max-agents <N>` | Cap maximum Ash summoned (1-8, including custom) | All selected |
| `--dry-run` | Show scope selection and Ash plan without summoning agents | Off |
| `--no-lore` | Disable Phase 0.5 Lore Layer (git history risk scoring) | Off |
| `--deep-lore` | Run Lore Layer on ALL files (default: Tier 1 only) | Off |
| `--deep` | Run multi-wave deep audit with deep investigation Ashes | On (default for audit) |
| `--standard` | Override default deep mode — run single-wave standard audit | Off |
| `--todos-dir <path>` | Override base todos directory (used by arc to scope todos to `tmp/arc/{id}/todos/`). Threaded to roundtable-circle Phase 5.4 | None |

**Note:** Unlike `/rune:appraise`, there is no `--partial` flag. Audit always scans the full project.

**Focus mode** selects only the relevant Ash (see [circle-registry.md](../roundtable-circle/references/circle-registry.md) for the mapping).

**Max agents** reduces team size when context or cost is a concern. Priority order: Ward Sentinel > Forge Warden > Veil Piercer > Pattern Weaver > Glyph Scribe > Knowledge Keeper > Codex Oracle.

## Preamble: Set Parameters

```javascript
// Parse depth: audit defaults to deep (unlike appraise which defaults to standard)
const depth = flags['--standard']
  ? "standard"
  : (flags['--deep'] !== false && (talisman?.audit?.always_deep !== false))
    ? "deep"
    : "standard"

const audit_id = Bash(`date +%Y%m%d-%H%M%S`).trim()
```

## Phase 0: Pre-flight

<!-- DELEGATION-CONTRACT: Changes to Phase 0 steps must be reflected in skills/arc/references/arc-delegation-checklist.md -->

```bash
# Scan all project files (excluding non-project directories)
all_files=$(find . -type f \
  ! -path '*/.git/*' \
  ! -path '*/node_modules/*' \
  ! -path '*/__pycache__/*' \
  ! -path '*/tmp/*' \
  ! -path '*/dist/*' \
  ! -path '*/build/*' \
  ! -path '*/.next/*' \
  ! -path '*/.venv/*' \
  ! -path '*/venv/*' \
  ! -path '*/target/*' \
  ! -path '*/.tox/*' \
  ! -path '*/vendor/*' \
  ! -path '*/.cache/*' \
  | sort)

# Optional: get branch name for metadata (not required — audit works without git)
branch=$(git branch --show-current 2>/dev/null || echo "n/a")
```

**Abort conditions:**
- No files found -> "No files to audit in current directory."
- Only non-reviewable files -> "No auditable code found."

**Note:** Unlike `/rune:appraise`, audit does NOT require a git repository.

### Load Custom Ashes

After scanning files, check for custom Ash config:

```
1. Read .claude/talisman.yml (project) or ~/.claude/talisman.yml (global)
2. If ashes.custom[] exists:
   a. Validate: unique prefixes, unique names, resolvable agents, count <= max
   b. Filter by workflows: keep only entries with "audit" in workflows[]
   c. Match triggers against all_files (extension + path match)
   d. Skip entries with fewer matching files than trigger.min_files
3. Merge validated custom Ash with built-in selections
4. Apply defaults.disable_ashes to remove any disabled built-ins
```

See [custom-ashes.md](../roundtable-circle/references/custom-ashes.md) for full schema and validation rules.

### Detect Codex Oracle

See [codex-detection.md](../roundtable-circle/references/codex-detection.md) for the canonical detection algorithm.

## Phase 0.5: Lore Layer (Risk Intelligence)

See [deep-mode.md](references/deep-mode.md) for the full Lore Layer implementation.

**Skip conditions**: non-git repo, `--no-lore`, `talisman.goldmask.layers.lore.enabled === false`, fewer than 5 commits in lookback window (G5 guard).

## Phase 1: Rune Gaze (Scope Selection)

Classify ALL project files by extension. See [rune-gaze.md](../roundtable-circle/references/rune-gaze.md).

**Apply `--focus` filter:** If `--focus <area>` is set, only summon Ash matching that area.
**Apply `--max-agents` cap:** If `--max-agents N` is set, limit selected Ash to N.

**Large codebase warning:** If total reviewable files > 150, log a coverage note.

### Dry-Run Exit Point

If `--dry-run` flag is set, display the plan and stop. No teams, tasks, state files, or agents are created.

## Delegate to Shared Orchestration

Set parameters and execute shared phases from [orchestration-phases.md](../roundtable-circle/references/orchestration-phases.md).

```javascript
// ── Resolve session identity ──
const configDir = Bash(`cd "\${CLAUDE_CONFIG_DIR:-$HOME/.claude}" 2>/dev/null && pwd -P`).trim()
const ownerPid = Bash(`echo $PPID`).trim()

const params = {
  scope: "full",
  depth,
  teamPrefix: "rune-audit",
  outputDir: `tmp/audit/${audit_id}/`,
  stateFilePrefix: "tmp/.rune-audit",
  identifier: audit_id,
  selectedAsh,
  fileList: all_files,
  timeoutMs: 900_000,   // 15 min (audits cover more files than reviews)
  label: "Audit",
  configDir, ownerPid,
  sessionId: "${CLAUDE_SESSION_ID}",
  maxAgents: flags['--max-agents'],
  workflow: "rune-audit",
  focusArea: flags['--focus'] || "full",
  flags, talisman
}

// Execute Phases 1-7 from orchestration-phases.md
// Phase 1: Setup (state file, output dir)
// Phase 2: Forge Team (inscription, signals, tasks)
// Phase 3: Summon (single wave or multi-wave based on depth)
// Phase 4: Monitor (waitForCompletion with audit timeouts)
// Phase 4.5: Doubt Seer (conditional)
// Phase 5: Aggregate (Runebinder → TOME.md)
// Phase 6: Verify (Truthsight)
// Phase 7: Cleanup (shutdown, TeamDelete, state update, Echo persist)
```

### Audit-Specific Post-Orchestration

After orchestration completes:

```javascript
// 1. Truthseer Validator (for high file counts)
if (reviewableFileCount > 100) {
  // Summon Truthseer Validator — see roundtable-circle SKILL.md Phase 5.5
  // Cross-references finding density against file importance
}

// 2. Auto-mend or interactive prompt (same as appraise)
if (totalFindings > 0) {
  AskUserQuestion({
    options: ["/rune:mend (Recommended)", "Review TOME manually", "/rune:rest"]
  })
}
```

## Error Handling

| Error | Recovery |
|-------|----------|
| Ash timeout (>5 min) | Proceed with partial results |
| Total timeout (>15 min) | Final sweep, collect partial results, report incomplete |
| Ash crash | Report gap in TOME.md |
| ALL Ash fail | Abort, notify user |
| Concurrent audit running | Warn, offer to cancel previous |
| File count exceeds 150 | Warn about partial coverage, proceed with capped budgets |
| Not a git repo | Works fine — audit uses `find`, not `git diff` |
| Codex CLI not installed | Skip Codex Oracle |
| Codex not authenticated | Skip Codex Oracle |
| Codex disabled in talisman.yml | Skip Codex Oracle |

## References

- [Deep Mode](references/deep-mode.md) — Lore Layer, deep pass, TOME merge
- [Orchestration Phases](../roundtable-circle/references/orchestration-phases.md) — Shared parameterized orchestration
- [Circle Registry](../roundtable-circle/references/circle-registry.md) — Ash-to-scope mapping, focus mode
- [Smart Selection](../roundtable-circle/references/smart-selection.md) — File assignment, budget enforcement
- [Wave Scheduling](../roundtable-circle/references/wave-scheduling.md) — Multi-wave deep scheduling
