# Batch Process Bot Comments

Processes comments in batches of BATCH_SIZE to protect context window. Includes hallucination checking to verify bot findings against actual code.

**Inputs**: `outputDir` with categorized JSON files, `BATCH_SIZE`, `HALLUCINATION_CHECK` flag
**Outputs**: Per-batch result files (`batch-{N}-results.json`), `allResults` array
**Preconditions**: Phase 4 categorization complete (unresolved-threads.json, bot-issue-comments.json exist)

## Phase 6a-6b: Merge and Split into Batches

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
```

## Phase 6c: Verify, Classify Each Batch

```
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

## Hallucination Check Algorithm

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
