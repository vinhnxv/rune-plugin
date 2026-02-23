# Arc Delegation Checklist

Canonical reference for which Phase 0 steps to execute when arc delegates to another command.
Each step is annotated: **RUN** (execute as-is), **SKIP** (arc handles this or not needed),
or **ADAPT** (run with arc-specific modifications).

<!-- NOTE: When adding new arc phases that delegate to commands, add a section here. -->
<!-- Cross-reference: appraise.md and audit.md Phase 0 sections contain DELEGATION-CONTRACT comments pointing here. -->

## Security Note

Arc must sanitize all variables before passing to delegated Phase 0 steps.
Use `SAFE_PATH_PATTERN` validation for file paths and write file lists to temp files
rather than inline interpolation (see appraise.md SEC-006). Variables from previous
phase artifacts (plan paths, file lists, team names) are validated at arc pre-flight,
but re-validate if transforming or concatenating.

## Phase 1: FORGE → `/rune:forge`

Already explicit in arc-phase-forge.md. Listed here for completeness.

| Step | Action | Reason |
|------|--------|--------|
| Scope confirmation (forge Phase 3) | **SKIP** | Arc is automated — no user prompt |
| Post-enhancement options (forge Phase 6) | **SKIP** | Arc continues to Phase 2 automatically |
| Forge Gaze topic matching | **RUN** | Section-level agent selection |
| Codex Oracle detection | **RUN** | Per `codex-detection.md`, if `forge` in `talisman.codex.workflows` |
| Custom Ash loading | **RUN** | `ashes.custom[]` filtered by `workflows: [forge]` |

## Phase 2: PLAN REVIEW (independent implementation)

Arc Phase 2 does NOT delegate to `/rune:devise` Phase 4 — it creates its own team (see
arc-phase-plan-review.md). This section documents feature parity with plan-review.md.

| Step | Action | Reason |
|------|--------|--------|
| Scroll review (4A) | **RUN** | Arc summons scroll-reviewer (already implemented) |
| Iterative refinement (4B) | **SKIP** | Arc has Phase 2.5 (PLAN REFINEMENT) for concerns |
| Automated verification gate (4B.5) | **SKIP** | Arc has Phase 2.7 (VERIFICATION GATE) |
| Technical review — decree-arbiter (4C) | **RUN** | Arc summons decree-arbiter (already implemented) |
| Technical review — knowledge-keeper (4C) | **RUN** | Arc summons knowledge-keeper (already implemented) |
| Codex Plan Reviewer (4C) | **RUN** | Per `codex-detection.md`, if `plan` in `talisman.codex.workflows` |
| Custom Ash for plan review | **SKIP** | No custom Ash workflow for plan review currently |

## Phase 5: WORK → `/rune:strive`

| Step | Action | Reason |
|------|--------|--------|
| Parse plan (work Phase 0) | **RUN** | Work needs to extract tasks from enriched plan |
| Environment setup (work Phase 0.5) | **ADAPT** | Branch already created by arc pre-flight; work detects and uses existing branch |
| Forge team (work Phase 1) | **RUN** | Work creates its own team |
| Codex Oracle detection | **RUN** | Per `codex-detection.md`, if `work` in `talisman.codex.workflows` |
| `--todos-dir` flag | **ADAPT** | Arc scopes todos to `tmp/arc/{id}/todos/`. Strive resolves to `{base}/work/` via `resolveTodosDir(args, talisman, "work")`. Only passed when `fileTodosEnabled && checkpoint.todos_base` |

## Phase 6: CODE REVIEW (deep) → `/rune:appraise --deep`

| Step | Action | Reason |
|------|--------|--------|
| Branch detection | **ADAPT** | Arc already knows the branch; pass as context, but review still needs `default_branch` for diff |
| Default branch detection | **RUN** | Review needs this to compute diff base |
| Changed files scope building | **RUN** | Review needs file inventory for Ash assignment |
| Scope summary display | **SKIP** | Arc is automated — no user display needed |
| Abort conditions check | **RUN** | If no changed files, review should no-op gracefully |
| Custom Ash loading | **RUN** | `ashes.custom[]` filtered by `workflows: [review]` (no-op if none configured) |
| Codex Oracle detection | **RUN** | Per `codex-detection.md`, if `review` in `talisman.codex.workflows` |
| `--todos-dir` flag | **ADAPT** | Arc scopes todos to `tmp/arc/{id}/todos/`. Appraise threads to roundtable-circle Phase 5.4 which resolves to `{base}/review/` via `resolveTodosDir(args, talisman, "review")`. Only passed when `fileTodosEnabled && checkpoint.todos_base` |

### Arc context adaptations for Phase 6

- `--deep` flag: **ALWAYS** — arc always passes `--deep` for multi-wave review (replaces former Phase 8 audit)
- Dry-run mode: **SKIP** — arc never does dry-run
- `--partial` flag: **SKIP** — arc always reviews full scope
- User-facing scope selection prompt: **SKIP** — arc is automated

## Phase 7: MEND → `/rune:mend`

| Step | Action | Reason |
|------|--------|--------|
| TOME path resolution | **ADAPT** | Arc provides TOME path from Phase 6 artifact |
| Parse TOME findings | **RUN** | Mend needs to group findings by file |
| Custom Ash for mend | **SKIP** | No custom Ash workflow for mend |
| `--todos-dir` flag | **ADAPT** | Arc scopes todos to `tmp/arc/{id}/todos/`. Mend uses `resolveTodosBase(args, talisman)` to scan all subdirectories (`{base}*/[0-9][0-9][0-9]-*.md`) for cross-source `finding_id` matching. Only passed when `fileTodosEnabled && checkpoint.todos_base` |

## Phase 5.7: GOLDMASK VERIFICATION → `/rune:goldmask`

Delegates to the standalone `/rune:goldmask` skill, which manages its own team and agents.

| Step | Action | Reason |
|------|--------|--------|
| Team lifecycle | **SKIP** | Goldmask skill creates/deletes its own team with `goldmask-` prefix |
| Agent summoning | **SKIP** | Goldmask skill summons its own investigation agents |
| Output collection | **RUN** | Arc copies `tmp/goldmask/GOLDMASK.md` → `tmp/arc/{id}/goldmask-verification.md` |
| Prediction comparison | **RUN** | If plan-time `risk-map.json` exists, compare predictions vs actuals |
| Cleanup | **ADAPT** | `prePhaseCleanup()` handles `goldmask-` prefixed teams via ARC_TEAM_PREFIXES |

### Arc context adaptations for Phase 5.7

- User-facing prompt: **SKIP** — arc is automated, goldmask runs silently
- Output path: **ADAPT** — copy goldmask output to arc artifact directory

## Phase 6.5: GOLDMASK CORRELATION (orchestrator-only)

Orchestrator-only phase — no delegation, no team creation. Reads Phase 5.7 + Phase 6 outputs.

| Step | Action | Reason |
|------|--------|--------|
| prePhaseCleanup | **SKIP** | Orchestrator-only, no team to clean |
| TOME path resolution | **ADAPT** | Use round-aware path (`tome-round-{N}.md`) for convergence cycles |
| Correlation logic | **RUN** | Deterministic file-level matching between TOME and Goldmask findings |
| Human review flagging | **RUN** | Caution >= 0.75 or WIDE blast radius → flag for Phase 7 mend |

### Convergence cycle behavior

On re-review rounds (`round > 0`), `goldmask_correlation` is reset to `pending` by verify-mend.md so it re-correlates with the new TOME. Goldmask verification is NOT re-run (blast radius doesn't change between mend cycles).

<!-- Phase 8 (AUDIT) delegation removed in v1.67.0. Audit coverage is now handled by
     Phase 6 `/rune:appraise --deep` (multi-wave review with investigation + dimension Ashes).
     See arc-phase-code-review.md for the updated delegation contract. -->
