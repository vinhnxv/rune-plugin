---
name: rune:review
description: |
  Multi-agent code review using Agent Teams. Summons up to 6 built-in Ashes
  (plus custom Ash from talisman.yml), each with their own 200k context window.
  Handles scope selection, team creation, review orchestration, aggregation, verification, and cleanup.

  <example>
  user: "/rune:review"
  assistant: "The Tarnished convenes the Roundtable Circle for review..."
  </example>
user-invocable: true
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
---

# /rune:review — Multi-Agent Code Review

Orchestrate a multi-agent code review using the Roundtable Circle architecture. Each Ash gets its own 200k context window via Agent Teams.

**Load skills**: `roundtable-circle`, `context-weaving`, `rune-echoes`, `rune-orchestration`, `codex-cli`

## Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--partial` | Review only staged files (`git diff --cached`) instead of full branch diff | Off (reviews all branch changes) |
| `--dry-run` | Show scope selection and Ash plan without summoning agents | Off |
| `--max-agents <N>` | Limit total Ash summoned (built-in + custom). Range: 1-8 | All selected |

**Partial mode** is useful for reviewing a subset of changes before committing, rather than the full branch diff against the default branch.

**Dry-run mode** executes Phase 0 (Pre-flight) and Phase 1 (Rune Gaze) only, then displays:
- Changed files classified by type
- Which Ash would be summoned
- File assignments per Ash (with context budget caps)
- Estimated team size

No teams, tasks, state files, or agents are created. Use this to preview scope before committing to a full review.

## Phase 0: Pre-flight

```bash
# Determine what to review
branch=$(git branch --show-current)
default_branch=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
if [ -z "$default_branch" ]; then
  default_branch=$(git rev-parse --verify origin/main >/dev/null 2>&1 && echo "main" || echo "master")
fi
repo_root=$(git rev-parse --show-toplevel)

# Get changed files — unified scope builder
if [ "--partial" in flags ]; then
  # Partial mode: staged files only (explicit choice — user knows what they're reviewing)
  changed_files=$(git -C "$repo_root" diff --cached --name-only)
else
  # Default: full scope — committed + staged + unstaged + untracked
  committed=$(git -C "$repo_root" diff --name-only --diff-filter=ACMR "${default_branch}...HEAD")
  staged=$(git -C "$repo_root" diff --cached --name-only --diff-filter=ACMR)
  unstaged=$(git -C "$repo_root" diff --name-only)
  untracked=$(git -C "$repo_root" ls-files --others --exclude-standard)
  # Merge and deduplicate, remove non-existent files and symlinks
  changed_files=$(echo "$committed"$'\n'"$staged"$'\n'"$unstaged"$'\n'"$untracked" | sort -u | grep -v '^$')
  changed_files=$(echo "$changed_files" | while read f; do
    [ -f "$repo_root/$f" ] && [ ! -L "$repo_root/$f" ] && echo "$f"
  done)
fi
```

**Scope summary** (displayed after file collection in non-partial mode):
```
Review scope:
  Committed: {N} files (vs {default_branch})
  Staged: {N} files
  Unstaged: {N} files (local modifications)
  Untracked: {N} files (new, not yet in git)
  Total: {N} unique files
```

**Abort conditions:**
- No changed files → "Nothing to review. Make some changes first."
- Only non-reviewable files (images, lock files) → "No reviewable changes found."
- All doc-extension files fell below line threshold AND code/infra files exist → summon only always-on Ashes (normal behavior — minor doc changes alongside code are noise)

**Docs-only override:** If ALL non-skip files are doc-extension and ALL fall below the line threshold (no code files at all), promote them so Knowledge Keeper is still summoned. This prevents a degenerate case where a docs-only diff silently skips all files. See `rune-gaze.md` for the full algorithm.

### Load Custom Ashes

After collecting changed files, check for custom Ash config:

```
1. Read .claude/talisman.yml (project) or ~/.claude/talisman.yml (global)
2. If ashes.custom[] exists:
   a. Validate: unique prefixes, unique names, resolvable agents, count ≤ max
   b. Filter by workflows: keep only entries with "review" in workflows[]
   c. Match triggers against changed_files (extension + path match)
   d. Skip entries with fewer matching files than trigger.min_files
3. Merge validated custom Ash with built-in selections
4. Apply defaults.disable_ashes to remove any disabled built-ins
```

See `roundtable-circle/references/custom-ashes.md` for full schema and validation rules.

### Detect Codex Oracle (CLI-Gated Built-in Ash)

After custom Ash loading, check whether the Codex Oracle should be summoned. Codex Oracle is a built-in Ash that wraps the OpenAI `codex` CLI, providing cross-model verification (GPT-5.3-codex alongside Claude). It is auto-detected and gracefully skipped when unavailable.

See `roundtable-circle/references/codex-detection.md` for the canonical detection algorithm.

**Note:** CLI detection is fast (no network call, <100ms). When Codex Oracle is selected, it counts toward the `max_ashes` cap. Codex Oracle findings use the `CDX` prefix and participate in standard dedup, TOME aggregation, and Truthsight verification.

## Phase 1: Rune Gaze (Scope Selection)

Classify changed files by extension. See `roundtable-circle/references/rune-gaze.md`.

```
for each file in changed_files:
  - *.py, *.go, *.rs, *.rb, *.java, etc.           → select Forge Warden
  - *.ts, *.tsx, *.js, *.jsx, etc.                  → select Glyph Scribe
  - Dockerfile, *.sh, *.sql, *.tf, CI/CD configs    → select Forge Warden (infra)
  - *.yml, *.yaml, *.json, *.toml, *.ini            → select Forge Warden (config)
  - *.md (>= 10 lines changed)                      → select Knowledge Keeper
  - .claude/**/*.md                                  → select Knowledge Keeper + Ward Sentinel (security boundary)
  - Unclassified (not in any group or skip list)     → select Forge Warden (catch-all)
  - Always: Ward Sentinel (security)
  - Always: Pattern Weaver (quality)

# Custom Ashes (from talisman.yml):
for each custom in validated_custom_ash:
  matching = files where extension in custom.trigger.extensions
                    AND (custom.trigger.paths is empty OR file starts with any path)
  if len(matching) >= custom.trigger.min_files:
    select custom.name with matching[:custom.context_budget]
```

Check for project overrides in `.claude/talisman.yml`.

### Dry-Run Exit Point

If `--dry-run` flag is set, display the plan and stop:

```
Dry Run — Review Plan
━━━━━━━━━━━━━━━━━━━━━

Branch: {branch} (vs {default_branch})
Changed files: {count}
  Backend:  {count} files
  Frontend: {count} files
  Docs:     {count} files
  Other:    {count} files (skipped)

Ash to summon: {count} ({built_in_count} built-in + {custom_count} custom)
  Built-in:
  - Forge Warden:      {file_count} files (cap: 30)
  - Ward Sentinel:     {file_count} files (cap: 20)
  - Pattern Weaver:    {file_count} files (cap: 30)
  - Glyph Scribe:      {file_count} files (cap: 25)  [conditional]
  - Knowledge Keeper:  {file_count} files (cap: 25)  [conditional]
  - Codex Oracle:      {file_count} files (cap: 20)  [conditional — requires codex CLI]

  Custom (from .claude/talisman.yml):       # Only shown if custom Ash exist
  - {name} [{prefix}]: {file_count} files (cap: {budget}, source: {source})

Dedup hierarchy: {hierarchy from settings or default}

To run the full review: /rune:review
```

Do NOT proceed to Phase 2. Exit here.

## Phase 2: Forge Team

```javascript
// 1. Check for concurrent review
// If tmp/.rune-review-{identifier}.json exists and < 30 min old, abort

// 2. Create output directory
Bash("mkdir -p tmp/reviews/{identifier}")

// 3. Write state file
Write("tmp/.rune-review-{identifier}.json", {
  team_name: "rune-review-{identifier}",
  started: timestamp,
  status: "active",
  expected_files: selectedAsh.map(r => `tmp/reviews/${identifier}/${r}.md`)
})

// 4. Generate inscription.json (see roundtable-circle/references/inscription-schema.md)
Write("tmp/reviews/{identifier}/inscription.json", { ... })

// 5. Pre-create guard: cleanup stale team if exists (see team-lifecycle-guard.md)
// Validate identifier before rm -rf
if (!/^[a-zA-Z0-9_-]+$/.test(identifier)) throw new Error("Invalid review identifier")
try { TeamDelete() } catch (e) {
  Bash("rm -rf ~/.claude/teams/rune-review-{identifier}/ ~/.claude/tasks/rune-review-{identifier}/ 2>/dev/null")
}
TeamCreate({ team_name: "rune-review-{identifier}" })

// 6. Create tasks (one per Ash)
for (const ash of selectedAsh) {
  TaskCreate({
    subject: `Review as ${ash}`,
    description: `Files: [...], Output: tmp/reviews/{identifier}/${ash}.md`,
    activeForm: `${ash} reviewing...`
  })
}
```

## Phase 3: Summon Ash

Summon ALL selected Ash in a **single message** (parallel execution):

<!-- NOTE: Ashes are summoned as general-purpose (not namespaced agent types) because
     Ash prompts are composite — each Ash embeds multiple review perspectives from
     agents/review/*.md. The agent file allowed-tools are NOT enforced at runtime.
     Tool restriction is enforced via prompt instructions (defense-in-depth).
     Future improvement: create composite Ash agent files with restricted allowed-tools. -->

```javascript
// Built-in Ash: load prompt from ash-prompts/{role}.md
Task({
  team_name: "rune-review-{identifier}",
  name: "{ash-name}",
  subagent_type: "general-purpose",
  prompt: /* Load from roundtable-circle/references/ash-prompts/{role}.md
             Substitute: {changed_files}, {output_path}, {task_id}, {branch}, {timestamp}
             // Codex Oracle additionally requires: {context_budget}, {codex_model}, {codex_reasoning}, {file_batch}
             // These are resolved from talisman.codex.* config. See codex-oracle.md header for full contract. */,
  run_in_background: true
})

// Custom Ash: use wrapper prompt template from custom-ashes.md
// The wrapper injects Truthbinding Protocol + Glyph Budget + Seal format
Task({
  team_name: "rune-review-{identifier}",
  name: "{custom.name}",
  subagent_type: "{custom.agent}",  // local name or plugin namespace
  prompt: /* Generate from wrapper template in roundtable-circle/references/custom-ashes.md
             Substitute: {name}, {file_list}, {output_dir}, {finding_prefix}, {context_budget} */,
  run_in_background: true
})
```

**IMPORTANT**: The Tarnished MUST NOT review code directly. Focus solely on coordination.

## Phase 4: Monitor

Poll TaskList with timeout guard until all tasks complete. Uses the shared polling utility — see [`skills/roundtable-circle/references/monitor-utility.md`](../skills/roundtable-circle/references/monitor-utility.md) for full pseudocode and contract.

```javascript
// See skills/roundtable-circle/references/monitor-utility.md
const result = waitForCompletion(teamName, ashCount, {
  timeoutMs: 600_000,        // 10 minutes
  staleWarnMs: 300_000,      // 5 minutes
  pollIntervalMs: 30_000,    // 30 seconds
  label: "Review"
  // No autoReleaseMs: review Ashes produce unique findings that can't be reclaimed by another Ash.
})

if (result.timedOut) {
  log(`Review completed with partial results: ${result.completed.length}/${ashCount} Ashes`)
}
```

**Stale detection**: If a task is `in_progress` for > 5 minutes, a warning is logged. No auto-release — review Ash findings are non-fungible (compare with `work.md`/`mend.md` which auto-release stuck tasks after 10 min).
**Total timeout**: Hard limit of 10 minutes. After timeout, a final sweep collects any results that completed during the last poll interval.

## Phase 5: Aggregate (Runebinder)

After all tasks complete (or timeout):

```javascript
Task({
  team_name: "rune-review-{identifier}",
  name: "runebinder",
  subagent_type: "general-purpose",
  prompt: `Read all findings from tmp/reviews/{identifier}/.
    Deduplicate using hierarchy from settings.dedup_hierarchy (default: SEC > BACK > DOC > QUAL > FRONT > CDX).
    Include custom Ash outputs and Codex Oracle (CDX prefix) in dedup — use their finding_prefix from config.
    Write unified summary to tmp/reviews/{identifier}/TOME.md.
    IMPORTANT: Use the TOME format from roundtable-circle/references/ash-prompts/runebinder.md.
    Every finding MUST be wrapped in <!-- RUNE:FINDING nonce="{session_nonce}" ... --> markers.
    The session_nonce is from inscription.json. Without these markers, /rune:mend cannot parse findings.
    See roundtable-circle/references/dedup-runes.md for dedup algorithm.`
})
```

### Zero-Finding Warning

After Runebinder produces TOME.md, check for suspiciously empty Ash outputs:

```javascript
// For each Ash that reviewed >15 files but produced 0 findings: flag in TOME
for (const ash of selectedAsh) {
  const ashOutput = Read(`tmp/reviews/${identifier}/${ash.name}.md`)
  const findingCount = (ashOutput.match(/<!-- RUNE:FINDING/g) || []).length
  const fileCount = ash.files.length

  if (fileCount > 15 && findingCount === 0) {
    warn(`${ash.name} reviewed ${fileCount} files with 0 findings — verify review thoroughness`)
    // Runebinder appends a NOTE (not a finding) to TOME.md:
    // "NOTE: {ash.name} reviewed {fileCount} files and reported no findings.
    //  This may indicate a thorough codebase or an incomplete review."
  }
}
```

This is a transparency flag, not a hard minimum. Zero findings on a small changeset is normal. Zero findings on 20+ files warrants a second look.

<!-- NOTE: "Phase 5.5" in review.md refers to Cross-Model Verification (Codex Oracle).
     Other pipelines use 5.5 for different sub-phases (audit: Truthseer Validator, arc: Gap Analysis). -->
## Phase 5.5: Cross-Model Verification (Codex Oracle)

This phase only runs if Codex Oracle was summoned (i.e., `codex-oracle` is in the Ash selection). It verifies Codex findings against actual source code before they enter the TOME, guarding against cross-model hallucinations.

**Why this is needed:** GPT models can fabricate file paths, invent code snippets, and reference non-existent patterns. Since Codex output is generated by a different model (GPT-5.3-codex), its findings are treated as untrusted until verified by Claude against the actual codebase.

```
1. Read Codex Oracle output from tmp/reviews/{identifier}/codex-oracle.md
   - If the file is missing or empty (<100 chars): skip verification, log "Codex Oracle: no output to verify"
   - If Codex Oracle timed out (partial output): verify what is available, note partial status

2. Parse all CDX-prefixed findings from the output

3. For each CDX finding, verify against actual source:

   a. FILE EXISTS CHECK
      - Read the file referenced in the finding
      - If the file does NOT exist:
        → Mark finding as HALLUCINATED (reason: "File does not exist")
        → Do NOT include in TOME

   b. CODE MATCH CHECK
      - Read actual code at the referenced line number (±2 lines for context)
      - Compare the Rune Trace snippet in the finding with the actual code
      - Use fuzzy matching (threshold from talisman.codex.verification.fuzzy_match_threshold, default: 0.7)
      - If the code does NOT match:
        → Mark finding as UNVERIFIED (reason: "Code at referenced line does not match Rune Trace")
        → Do NOT include in TOME

   c. CROSS-ASH CORRELATION
      - Read findings from all other Ash outputs (Forge Warden, Ward Sentinel, Pattern Weaver, etc.)
      - Check if any other Ash flagged an issue in the same file within ±5 lines
      - If a cross-match is found:
        → Mark finding as CONFIRMED (reason: "Cross-validated by Claude Ash")
        → Apply cross-model confidence bonus (talisman.codex.verification.cross_model_bonus, default: +0.15)
      - If no cross-match but file and code verified:
        → Mark finding as CONFIRMED (reason: "Code verified, unique finding from Codex perspective")

4. Rewrite Codex Oracle output with verification annotations:
   - Only CONFIRMED findings are kept
   - HALLUCINATED and UNVERIFIED findings are removed from the output
   - Add verification summary header to the rewritten file

5. Log verification summary:
   Cross-Model Verification:
     Confirmed: {count} ({cross_validated_count} cross-validated with Claude Ash)
     Hallucinated: {count} (removed — fabricated file/code references)
     Unverified: {count} (removed — code mismatch at referenced lines)
```

**Timeout note:** The review pipeline has a 10-minute total timeout (Phase 4). If Codex Oracle produces partial results due to timeout, Phase 5.5 verifies whatever output is available. Partial results are acceptable — it is better to have 5 verified findings than 20 unverified ones.

**Performance:** Phase 5.5 is orchestrator-only (no additional teammates). It reads files that are already in the review scope, so no new file I/O beyond what Ashes already performed.

## Phase 6: Verify (Truthsight)

If inscription.json has `verification.enabled: true`:

1. **Layer 0**: Lead runs grep-based inline checks (file paths exist, line numbers valid)
2. **Layer 2**: Summon Truthsight Verifier for P1 findings (see `rune-orchestration/references/verifier-prompt.md`)
3. Flag any HALLUCINATED findings

## Phase 7: Cleanup & Echo Persist

```javascript
// 1. Shutdown all Ash + utility teammates (runebinder from Phase 5)
const allTeammates = [...allAsh, "runebinder"]
for (const teammate of allTeammates) {
  SendMessage({ type: "shutdown_request", recipient: teammate })
}

// 2. Wait for shutdown approvals (max 30s)

// 3. Cleanup team with fallback (see team-lifecycle-guard.md)
// identifier validated at Phase 2: /^[a-zA-Z0-9_-]+$/
try { TeamDelete() } catch (e) {
  Bash("rm -rf ~/.claude/teams/rune-review-{identifier}/ ~/.claude/tasks/rune-review-{identifier}/ 2>/dev/null")
}

// 4. Update state file to completed
Write("tmp/.rune-review-{identifier}.json", {
  team_name: "rune-review-{identifier}",
  started: timestamp,
  status: "completed",
  completed: new Date().toISOString(),
  expected_files: selectedAsh.map(r => `tmp/reviews/${identifier}/${r}.md`)
})

// 5. Persist learnings to Rune Echoes (if .claude/echoes/ exists)
//    Extract P1/P2 patterns from TOME.md and write as Inscribed entries
//    See rune-echoes skill for entry format and write protocol
if (exists(".claude/echoes/reviewer/")) {
  patterns = extractRecurringPatterns("tmp/reviews/{identifier}/TOME.md")
  for (const pattern of patterns) {
    appendEchoEntry(".claude/echoes/reviewer/MEMORY.md", {
      layer: "inscribed",
      source: `rune:review ${identifier}`,
      confidence: pattern.confidence,
      evidence: pattern.evidence,
      content: pattern.summary
    })
  }
}

// 6. Read and present TOME.md to user
Read("tmp/reviews/{identifier}/TOME.md")

// 7. Offer next steps based on findings
const tomeContent = Read(`tmp/reviews/${identifier}/TOME.md`)
const p1Count = (tomeContent.match(/severity="P1"/g) || []).length
const p2Count = (tomeContent.match(/severity="P2"/g) || []).length
const totalFindings = p1Count + p2Count

if (totalFindings > 0) {
  AskUserQuestion({
    questions: [{
      question: `Review complete: ${p1Count} critical + ${p2Count} major findings. What next?`,
      header: "Next",
      options: [
        { label: "/rune:mend (Recommended)", description: `Auto-fix ${totalFindings} P1/P2 findings from TOME` },
        { label: "Review TOME manually", description: "Read findings and fix manually" },
        { label: "/rune:rest", description: "Clean up tmp/ artifacts" }
      ],
      multiSelect: false
    }]
  })
  // /rune:mend → Skill("rune:mend", `tmp/reviews/${identifier}/TOME.md`)
  // Manual → user reviews TOME.md
  // /rune:rest → Skill("rune:rest")
} else {
  log("No P1/P2 findings. Codebase looks clean.")
}
```

## Error Handling

| Error | Recovery |
|-------|----------|
| Ash timeout (>5 min) | Proceed with partial results |
| Total timeout (>10 min) | Final sweep, collect partial results, report incomplete |
| Ash crash | Report gap in TOME.md |
| ALL Ash fail | Abort, notify user |
| Concurrent review running | Warn, offer to cancel previous |
| Codex CLI not installed | Skip Codex Oracle, log: "CLI not found, skipping (install: npm install -g @openai/codex)" |
| Codex CLI broken (can't execute) | Skip Codex Oracle, log: "CLI found but cannot execute — reinstall" |
| Codex not authenticated | Skip Codex Oracle, log: "not authenticated — run `codex login`" |
| Codex disabled in talisman.yml | Skip Codex Oracle, log: "disabled via talisman.yml" |
| Codex exec timeout (>10 min) | Codex Oracle reports partial results, log: "timeout — reduce context_budget" |
| Codex exec auth error at runtime | Log: "authentication required — run `codex login`", skip batch |
| Codex exec failure (non-zero exit) | Classify error per `codex-detection.md`, log user-facing message, other Ashes unaffected |
| jq unavailable | Codex Oracle uses raw text fallback instead of JSONL parsing |
