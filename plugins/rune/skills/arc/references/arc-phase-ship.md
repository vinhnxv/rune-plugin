# Phase 9: SHIP — PR Creation

Orchestrator-only phase (no team). Creates a GitHub PR after audit completes.

**Team**: None (orchestrator-only — runs inline after Phase 8)
**Tools**: Bash (git + gh), Read, Write
**Timeout**: 5 min (PHASE_TIMEOUTS.ship = 300_000)

**Inputs**:
- Checkpoint (with `plan_file`, `id`, `phases`, `convergence`)
- `arcConfig.ship` (resolved via `resolveArcConfig()`)
- Audit report (`tmp/arc/{id}/audit-report.md`)

**Outputs**: `tmp/arc/{id}/pr-body.md`, `checkpoint.pr_url`

**Consumers**: Phase 9.5 MERGE (needs `checkpoint.pr_url`), Completion Report, Completion Stamp

> **Note**: `sha256()`, `updateCheckpoint()`, `exists()`, and `warn()` are dispatcher-provided utilities available in the arc orchestrator context. Phase reference files call these without import.

## Pre-checks

1. Check `arcConfig.ship.auto_pr` -- if false, skip phase entirely
2. Verify `gh` CLI availability and authentication (`gh auth status`)
3. Verify current branch is not main/master (detached HEAD also skipped)
4. Verify there are commits to push (`git rev-list --count`)
5. Validate branch names against `BRANCH_RE`

## Algorithm

```javascript
updateCheckpoint({ phase: "ship", status: "in_progress", phase_sequence: 9, team_name: null })

// ENV: Disable gh interactive prompts in automation (SEC-DECREE-003 / concern C-7)
// Set before ALL gh commands in this phase
const GH_ENV = 'GH_PROMPT_DISABLED=1'

// 1. Pre-checks
if (!arcConfig.ship.auto_pr) {
  log("Ship phase skipped -- auto_pr is disabled in config")
  updateCheckpoint({ phase: "ship", status: "skipped" })
  return
}

const ghAvailable = Bash(`${GH_ENV} command -v gh >/dev/null 2>&1 && gh auth status 2>&1 | grep -q 'Logged in' && echo 'ok'`).trim() === "ok"
if (!ghAvailable) {
  warn("Ship phase: gh CLI not available or not authenticated. Skipping PR creation.")
  warn("Install: https://cli.github.com/ -- then run: gh auth login")
  updateCheckpoint({ phase: "ship", status: "skipped" })
  return
}

const currentBranch = Bash("git branch --show-current").trim()
const defaultBranch = Bash("git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@'").trim()
  || (Bash("git rev-parse --verify origin/main 2>/dev/null").exitCode === 0 ? "main" : "master")

if (currentBranch === defaultBranch || currentBranch === "") {
  warn("Ship phase: On default branch or detached HEAD -- skipping")
  updateCheckpoint({ phase: "ship", status: "skipped" })
  return
}

// Validate branch names (security -- before any shell interpolation)
const BRANCH_RE = /^[a-zA-Z0-9][a-zA-Z0-9._\/-]*$/
if (!BRANCH_RE.test(currentBranch) || !BRANCH_RE.test(defaultBranch)) {
  warn("Ship phase: Invalid branch name -- skipping")
  updateCheckpoint({ phase: "ship", status: "skipped" })
  return
}

// Verify there are commits to push
const commitCount = Bash(`git rev-list --count "${defaultBranch}".."${currentBranch}"`).trim()
if (commitCount === "0") {
  warn("Ship phase: No commits to push -- skipping PR creation")
  updateCheckpoint({ phase: "ship", status: "skipped" })
  return
}

// 2. Push branch
const pushResult = Bash(`git push -u origin -- "${currentBranch}"`)
if (pushResult.exitCode !== 0) {
  warn("Ship phase: Push failed. Create PR manually: git push -u origin " + currentBranch)
  updateCheckpoint({ phase: "ship", status: "failed" })
  return
}

// 3. Generate PR title from plan frontmatter
const planContent = Read(checkpoint.plan_file)
const titleMatch = planContent.match(/^---\n[\s\S]*?^title:\s*(.+?)$/m)
const planTitle = titleMatch ? titleMatch[1].trim() : basename(checkpoint.plan_file, '.md').replace(/^\d{4}-\d{2}-\d{2}-/, '')
const typeMatch = planContent.match(/^type:\s*(\w+)/m)
const planType = typeMatch ? typeMatch[1] : 'feat'
const prTitle = `${planType}: ${planTitle}`
const safePrTitle = prTitle.replace(/[^a-zA-Z0-9 ._\-:()]/g, '').slice(0, 70) || "Arc: work completed"

// 4. Build PR body
const diffStat = Bash(`git diff --stat "${defaultBranch}"..."${currentBranch}"`).trim()
const auditSummary = exists(`tmp/arc/${id}/audit-report.md`)
  ? Read(`tmp/arc/${id}/audit-report.md`).split('\n').slice(0, 20).join('\n')
  : "Audit report not available"

// Read talisman PR settings
const monitoringRequired = arcConfig.ship.pr_monitoring
const coAuthors = talisman?.work?.co_authors ?? []
const validCoAuthors = coAuthors.filter(a => /^[^<>\n]+\s+<[^@\n]+@[^>\n]+>$/.test(a))
const coAuthorLines = validCoAuthors.map(a => `Co-Authored-By: ${a}`).join('\n')

const prBody = `## Summary

Implemented from plan: \`${checkpoint.plan_file}\`
Pipeline: \`/rune:arc\` (${Object.values(checkpoint.phases).filter(p => p.status === "completed").length} phases completed)

### Changes
\`\`\`
${diffStat}
\`\`\`

### Arc Pipeline Results
- **Commits**: ${commitCount} incremental commits, each ward-checked
- **Code Review**: ${exists(`tmp/arc/${id}/tome.md`) ? "TOME generated" : "N/A"}
- **Mend**: ${checkpoint.convergence?.history?.length ?? 0} convergence cycle(s)
- **Audit**: Completed

### Audit Summary
${auditSummary}

${monitoringRequired ? `## Post-Deploy Monitoring
<!-- Fill in before merging -->
- **What to monitor**:
- **Expected healthy behavior**:
- **Failure signals / rollback trigger**:
- **Validation window**:
` : ""}
---
Generated with [Claude Code](https://claude.ai/code) via Rune Plugin (/rune:arc)
${coAuthorLines}`

Write(`tmp/arc/${id}/pr-body.md`, prBody)

// 5. Create PR
// Validate labels array before .map() (SEC-DECREE-002 / concern #13)
const labelsArray = Array.isArray(arcConfig.ship.labels) ? arcConfig.ship.labels : []
const draftFlag = arcConfig.ship.draft ? "--draft" : ""
const labelFlag = labelsArray.length > 0
  ? labelsArray.map(l => `--label "${l.replace(/[^a-zA-Z0-9 ._\-]/g, '')}"`).join(' ')
  : ""

// Always specify --base explicitly (concern C-2 / cross-reviewer agreement)
const prResult = Bash(`${GH_ENV} gh pr create --title "${safePrTitle}" --base "${defaultBranch}" --body-file "tmp/arc/${id}/pr-body.md" ${draftFlag} ${labelFlag}`.trim())

if (prResult.exitCode !== 0) {
  // Check if PR already exists (branch already has an open PR)
  const existingPr = Bash(`${GH_ENV} gh pr view --json url -q .url 2>/dev/null`).trim()
  if (existingPr) {
    log(`PR already exists: ${existingPr}`)
    checkpoint.pr_url = existingPr
    updateCheckpoint({
      phase: "ship", status: "completed",
      artifact: `tmp/arc/${id}/pr-body.md`,
      artifact_hash: sha256(Read(`tmp/arc/${id}/pr-body.md`)),
      phase_sequence: 9, team_name: null
    })
    return
  }
  warn("Ship phase: PR creation failed. Branch was pushed. Create PR manually: gh pr create")
  updateCheckpoint({ phase: "ship", status: "failed" })
  return
}

const prUrl = prResult.stdout.trim()
log(`PR created: ${prUrl}`)

// 6. Update checkpoint
checkpoint.pr_url = prUrl
updateCheckpoint({
  phase: "ship", status: "completed",
  artifact: `tmp/arc/${id}/pr-body.md`,
  artifact_hash: sha256(Read(`tmp/arc/${id}/pr-body.md`)),
  phase_sequence: 9, team_name: null
})
```

## Error Handling

| Condition | Action |
|-----------|--------|
| `auto_pr` disabled | Phase skipped -- proceed to merge (also skipped) or completion |
| gh CLI missing/unauthenticated | Phase skipped -- warn user, proceed to completion |
| On default branch | Phase skipped -- no PR needed |
| No commits to push | Phase skipped -- nothing to ship |
| Push fails | Phase failed -- branch not pushed, user creates PR manually |
| PR creation fails | Check for existing PR; if none, phase failed -- branch was pushed, user creates PR manually |
| Invalid branch name | Phase skipped -- security guard prevents shell injection |

## Failure Policy

Skip PR creation, proceed to completion report. User creates PR manually. Branch is pushed (if push succeeded), so `gh pr create` from terminal works.

## Crash Recovery

Orchestrator-only phase with no team -- minimal crash surface.

| Resource | Location |
|----------|----------|
| PR body file | `tmp/arc/{id}/pr-body.md` |
| Checkpoint state | `.claude/arc/{id}/checkpoint.json` (phase: "ship") |

Recovery: On `--resume`, if ship phase is `in_progress`, re-run from the beginning. Push is idempotent. PR creation checks for existing PR first.
