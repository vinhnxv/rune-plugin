---
name: resolve-all-gh-pr-comments
description: |
  Batch resolve all unresolved PR review comments. Fetches review threads
  AND issue comments (bot feedback) with pagination. Categorizes, auto-resolves
  outdated, groups related comments, and batches fixes into a single commit.
  Handles all known review bots with hallucination checking.
  Keywords: resolve all, PR comments, batch, review, bot, GitHub.

  <example>
  user: "/rune:resolve-all-gh-pr-comments 42"
  assistant: "Fetching all unresolved comments for PR #42..."
  </example>

  <example>
  user: "/rune:resolve-all-gh-pr-comments"
  assistant: "Detecting current PR from branch..."
  </example>
user-invocable: true
disable-model-invocation: false
argument-hint: "<pr_number>"
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - AskUserQuestion
---

# Resolve All GitHub PR Comments

Batch-resolve all unresolved PR review comments — both review thread comments (line-level)
and issue comments (PR-level from bots). Supports pagination for large PRs, hallucination
checking for bot findings, and grouped batch processing.

## Prerequisites

- `gh` CLI installed and authenticated
- Current directory is a git repository with a GitHub remote
- PR exists and has unresolved comments

## Phase 0: Parse Arguments & Resolve PR

```
INPUT: $ARGUMENTS → PR number or empty (auto-detect)

if $ARGUMENTS is empty:
  prNumber = Bash("GH_PROMPT_DISABLED=1 gh pr view --json number -q '.number' 2>/dev/null")
  if prNumber is empty:
    AskUserQuestion("No PR found for current branch. Please provide a PR number.")
    exit
else:
  prNumber = parseInt($ARGUMENTS)

# Validate PR number is a positive integer
if prNumber does not match /^[1-9][0-9]*$/:
  error("Invalid PR number: must be a positive integer")
  exit
```

## Phase 1: Resolve Repository & Configuration

```
# CONCERN 5: Explicitly extract owner/repo for GraphQL
owner = Bash("GH_PROMPT_DISABLED=1 gh repo view --json owner -q '.owner.login'")
repo = Bash("GH_PROMPT_DISABLED=1 gh repo view --json name -q '.name'")

if owner is empty or repo is empty:
  error("Cannot resolve repository owner/name. Ensure gh CLI is configured.")
  exit

# Read talisman config for bot_review settings
talisman = readTalisman()
botConfig = talisman?.arc?.ship?.bot_review ?? {}

BATCH_SIZE = botConfig.max_comment_batch_size ?? 10
AUTO_RESOLVE_OUTDATED = botConfig.auto_resolve_outdated ?? true
HALLUCINATION_CHECK = botConfig.hallucination_check ?? true
KNOWN_BOTS = botConfig.known_bots ?? [
  "gemini-code-assist[bot]",
  "coderabbitai[bot]",
  "copilot[bot]",
  "cubic-dev-ai[bot]",
  "chatgpt-codex-connector[bot]"
]
QUALITY_COMMANDS = botConfig.quality_commands ?? []
```

## Phase 2: Checkout PR Branch

```
# Checkout the PR branch to have the correct code context
Bash("GH_PROMPT_DISABLED=1 gh pr checkout ${prNumber}")
```

## Phase 3: Paginated Fetch — Write to Tmp Files

Fetch ALL comments to tmp files to avoid loading everything into context at once.

```
outputDir = "tmp/pr-comments/${prNumber}"
Bash("mkdir -p '${outputDir}'")

# 3a. Fetch review threads via GraphQL with cursor pagination
# CRITICAL: Use $endCursor (not $cursor) for gh --paginate compatibility
Bash("GH_PROMPT_DISABLED=1 gh api graphql --paginate -f query='
query(\$endCursor: String) {
  repository(owner: \"${owner}\", name: \"${repo}\") {
    pullRequest(number: ${prNumber}) {
      reviewThreads(first: 100, after: \$endCursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          isResolved
          isOutdated
          comments(first: 10) {
            nodes {
              id
              databaseId
              author { login }
              body
              path
              line
              url
              createdAt
              updatedAt
            }
          }
        }
      }
    }
  }
}' > '${outputDir}/review-threads.json'")

# 3b. Fetch issue comments (REST, paginated) — bot summary comments
Bash("GH_PROMPT_DISABLED=1 gh api --paginate 'repos/${owner}/${repo}/issues/${prNumber}/comments?per_page=100' > '${outputDir}/issue-comments.json'")

# 3c. Fetch PR review comments (REST, paginated) — inline bot comments
Bash("GH_PROMPT_DISABLED=1 gh api --paginate 'repos/${owner}/${repo}/pulls/${prNumber}/comments?per_page=100' > '${outputDir}/review-comments.json'")
```

## Phase 4: Categorize from Tmp Files

Extract and categorize using `jq` — never load all comments into agent context.

```
# Build bot login regex pattern for jq
botPattern = KNOWN_BOTS
  .map(b => b.replace("[", "\\[").replace("]", "\\]"))
  .join("|")

# 4a. Extract unresolved, non-outdated review threads
Bash("jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false and .isOutdated == false)]' '${outputDir}/review-threads.json' > '${outputDir}/unresolved-threads.json'")

# 4b. Extract outdated threads (candidates for auto-resolve)
Bash("jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false and .isOutdated == true)]' '${outputDir}/review-threads.json' > '${outputDir}/outdated-threads.json'")

# 4c. Extract bot issue comments
Bash("jq '[.[] | select(.user.login | test(\"${botPattern}\"))]' '${outputDir}/issue-comments.json' > '${outputDir}/bot-issue-comments.json'")

# 4d. Extract bot review comments (inline)
Bash("jq '[.[] | select(.user.login | test(\"${botPattern}\"))]' '${outputDir}/review-comments.json' > '${outputDir}/bot-review-comments.json'")

# 4e. Count categories
unresolvedCount = Bash("jq 'length' '${outputDir}/unresolved-threads.json'").trim()
outdatedCount = Bash("jq 'length' '${outputDir}/outdated-threads.json'").trim()
botIssueCount = Bash("jq 'length' '${outputDir}/bot-issue-comments.json'").trim()
botReviewCount = Bash("jq 'length' '${outputDir}/bot-review-comments.json'").trim()

log("Found: ${unresolvedCount} unresolved threads, ${outdatedCount} outdated, ${botIssueCount} bot issue comments, ${botReviewCount} bot review comments")
```

## Phase 5: Auto-Resolve Outdated Threads

```
if AUTO_RESOLVE_OUTDATED and outdatedCount > 0:
  # Resolve each outdated thread via GraphQL mutation
  Bash("jq -r '.[].id' '${outputDir}/outdated-threads.json' | while read tid; do
    # Validate thread ID format before interpolation
    if echo \"$tid\" | grep -qE '^[A-Za-z0-9_=-]+$'; then
      GH_PROMPT_DISABLED=1 gh api graphql -f query=\"mutation { resolveReviewThread(input: {threadId: \\\"$tid\\\"}) { thread { isResolved } } }\" 2>/dev/null
    fi
  done")
  log("Auto-resolved ${outdatedCount} outdated review threads.")
```

## Phase 6: Batch-Process Bot Comments

Process comments in batches of BATCH_SIZE to protect context window.

```
# 6a. Merge bot issue comments + unresolved threads into a single actionable list
Bash("jq -s 'add // []' '${outputDir}/bot-issue-comments.json' '${outputDir}/unresolved-threads.json' > '${outputDir}/actionable-all.json'")
totalActionable = Bash("jq 'length' '${outputDir}/actionable-all.json'").trim()

if totalActionable == 0:
  log("No actionable bot comments or unresolved threads found.")
  # Write summary report
  Write("${outputDir}/summary.md", "# PR Comment Resolution Summary\n\nPR: #${prNumber}\nOutdated auto-resolved: ${outdatedCount}\nActionable comments: 0\nNo fixes needed.")
  exit

# 6b. Split into batches
numBatches = ceil(totalActionable / BATCH_SIZE)
for batch in 0..numBatches-1:
  start = batch * BATCH_SIZE
  Bash("jq '.[${start}:${start + BATCH_SIZE}]' '${outputDir}/actionable-all.json' > '${outputDir}/batch-${batch}.json'")

# 6c. For each batch: read, verify, classify
allResults = []
for batch in 0..numBatches-1:
  batchFile = "${outputDir}/batch-${batch}.json"
  batchContent = Read(batchFile)

  for each comment in batchContent:
    result = { comment_id: comment.id, url: comment.url }

    # Determine comment type and extract finding details
    if comment has .path (review thread):
      result.type = "review_thread"
      result.file = comment.comments.nodes[0].path
      result.line = comment.comments.nodes[0].line
      result.body = comment.comments.nodes[0].body
      result.author = comment.comments.nodes[0].author.login
    else (issue comment):
      result.type = "issue_comment"
      result.body = comment.body
      result.author = comment.user.login

    # Hallucination check (if enabled)
    if HALLUCINATION_CHECK and result.file:
      result.verdict = verifyBotFinding(result)
    else:
      result.verdict = "NEEDS_REVIEW"

    allResults.append(result)

  Write("${outputDir}/batch-${batch}-results.json", JSON.stringify(batchResults))
```

### Hallucination Check Algorithm

```
function verifyBotFinding(finding):
  # 1. Read the actual file at the referenced path
  fileContent = Read(finding.file)
  if fileContent is empty:
    return { verdict: "NOT_APPLICABLE", reason: "File not found" }

  # 2. Check if the referenced line still exists
  lines = fileContent.split('\n')
  if finding.line and (finding.line > lines.length):
    return { verdict: "ALREADY_ADDRESSED", reason: "Line no longer exists" }

  # 3. Check if a recent commit already addressed the concern
  recentCommits = Bash("git log --oneline -5 -- '${finding.file}'")
  # Look for fix-related keywords in commit messages

  # 4. Analyze the actual code vs the bot's concern
  # Read surrounding context (finding.line +/- 10 lines)
  # Compare bot's claim against actual code behavior

  # 5. Return verdict: VALID | FALSE_POSITIVE | ALREADY_ADDRESSED | NOT_APPLICABLE
```

## Phase 7: Present Analysis to User

```
# Group results by verdict
validFindings = allResults.filter(r => r.verdict.verdict == "VALID")
falsePositives = allResults.filter(r => r.verdict.verdict == "FALSE_POSITIVE")
alreadyAddressed = allResults.filter(r => r.verdict.verdict == "ALREADY_ADDRESSED")
notApplicable = allResults.filter(r => r.verdict.verdict == "NOT_APPLICABLE")
needsReview = allResults.filter(r => r.verdict.verdict == "NEEDS_REVIEW")

# Present summary
log("## Comment Analysis Summary")
log("- Valid findings (will fix): ${validFindings.length}")
log("- False positives (will dismiss): ${falsePositives.length}")
log("- Already addressed: ${alreadyAddressed.length}")
log("- Not applicable: ${notApplicable.length}")
log("- Needs manual review: ${needsReview.length}")

# For each group that needs user input, present details
if needsReview.length > 0:
  for each group of related needsReview comments:
    AskUserQuestion("How should I handle these comments?\n${groupDetails}\n\nOptions: fix / dismiss / skip")
    # Record user decision

if validFindings.length > 0:
  AskUserQuestion("Found ${validFindings.length} valid bot findings. Proceed with fixes?\n${validSummary}")
```

## Phase 8: Implement Fixes

```
# 8a. Collect all approved fixes (valid + user-approved)
fixPlan = buildFixPlan(validFindings, approvedNeedsReview)

# 8b. Group by file to minimize Edit operations
fixesByFile = groupBy(fixPlan, 'file')

# 8c. Implement fixes file by file
for each [file, fixes] in fixesByFile:
  Read(file)
  for each fix in fixes (sorted by line descending to avoid offset drift):
    Edit(file, fix.oldCode, fix.newCode)

# 8d. Run quality checks (once, after all fixes)
for each cmd in QUALITY_COMMANDS:
  result = Bash(cmd)
  if result.exitCode != 0:
    warn("Quality check failed: ${cmd}")
    AskUserQuestion("Quality check '${cmd}' failed. Continue anyway?")

# 8e. Single commit + push
Bash("git add -A && git commit -m 'fix: resolve PR review comments from bot feedback'")
Bash("git push")
commitSha = Bash("git rev-parse HEAD").trim()
```

## Phase 9: Reply to Resolved Comments

```
# 9a. Reply to review thread comments
for each fix in resolvedThreadFixes:
  # Validate thread ID format
  threadId = fix.comment_id
  if threadId matches /^[A-Za-z0-9_=-]+$/:
    # Post reply on the review thread
    Bash("GH_PROMPT_DISABLED=1 gh api graphql -f query='mutation {
      addPullRequestReviewComment(input: {
        pullRequestReviewId: \"${fix.review_id}\",
        body: \"Addressed in ${commitSha}\",
        inReplyTo: \"${fix.comment_id}\"
      }) { comment { id } }
    }'")
    # Resolve the thread
    Bash("GH_PROMPT_DISABLED=1 gh api graphql -f query='mutation {
      resolveReviewThread(input: {threadId: \"${threadId}\"}) {
        thread { isResolved }
      }
    }'")

# 9b. Reply to bot issue comments
for each fix in resolvedIssueCommentFixes:
  commentId = fix.comment_id
  if commentId matches /^[0-9]+$/:
    Bash("GH_PROMPT_DISABLED=1 gh api repos/${owner}/${repo}/issues/comments/${commentId}/replies -f body='Addressed in ${commitSha}'")

# 9c. Reply to dismissed/false-positive comments
for each dismissed in falsePositives:
  Bash("GH_PROMPT_DISABLED=1 gh api ... -f body='Reviewed and dismissed: ${dismissed.reason}'")
```

## Phase 10: Summary Report

```
summary = """
# PR Comment Resolution Summary

PR: #${prNumber}
Repository: ${owner}/${repo}

## Statistics
- Outdated threads auto-resolved: ${outdatedCount}
- Valid findings fixed: ${validFindings.length}
- False positives dismissed: ${falsePositives.length}
- Already addressed: ${alreadyAddressed.length}
- Not applicable: ${notApplicable.length}
- Manually reviewed: ${needsReview.length}
- Commit: ${commitSha}

## Fixes Applied
${fixPlan.map(f => "- ${f.file}:${f.line} — ${f.summary}").join('\n')}

## Dismissed Findings
${falsePositives.map(f => "- ${f.author}: ${f.body.slice(0, 80)}... — ${f.reason}").join('\n')}
"""

Write("${outputDir}/summary.md", summary)
log(summary)
```

## Security Constraints

- **SEC-DECREE-003**: All `gh` commands prefixed with `GH_PROMPT_DISABLED=1`
- **Input validation**: PR number validated as positive integer before shell interpolation
- **Thread ID validation**: GraphQL thread IDs validated with `/^[A-Za-z0-9_=-]+$/` before mutation
- **Bot name validation**: Known bot names read from talisman config, escaped for regex
- **No context overload**: Comments written to tmp files and processed in BATCH_SIZE batches
- **Quality commands**: Only executed from talisman config (user-controlled)

## Talisman Configuration

All behavior is configurable via `arc.ship.bot_review` in `.claude/talisman.yml`:

| Key | Default | Description |
|-----|---------|-------------|
| `max_comment_batch_size` | `10` | Comments per processing batch |
| `auto_resolve_outdated` | `true` | Auto-resolve outdated review threads |
| `hallucination_check` | `true` | Verify bot findings against actual code |
| `known_bots` | 5 bots | List of known review bot usernames |
| `quality_commands` | `[]` | Commands to run after fixes (e.g., lint, typecheck) |

## Error Handling

| Error | Action |
|-------|--------|
| `gh` not installed | Exit with instructions to install GitHub CLI |
| PR not found | Exit with clear error message |
| GraphQL rate limit | Retry with exponential backoff (max 3 attempts) |
| Quality check fails | AskUserQuestion — user decides to continue or abort |
| No actionable comments | Exit cleanly with summary (no fixes needed) |
| Pagination timeout | Write partial results, process what was fetched |
