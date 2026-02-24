# Fix and Reply Protocol

Detailed implementation for Phases 5-9 of `/rune:resolve-gh-pr-comment`. Read and execute when the user approves a fix action.

## Phase 5: Implement Fix

If user chose to fix, read the file, implement the change, and verify.

```javascript
if (userChoice === "Skip") {
  log("Skipped. No action taken.")
  return
}

if (userChoice === "Reply only") {
  // Skip to Phase 8
  goto Phase8
}

if (userChoice === "Mark as false positive") {
  // Skip to Phase 8 with false positive reply
  goto Phase8_FalsePositive
}

// "Fix and reply" or "Fix, reply, and resolve"
const shouldResolve = resolveFlag || userChoice === "Fix, reply, and resolve"

if (!filePath) {
  // PR-level comment -- ask user which file to modify
  log("This is a PR-level comment without a specific file reference.")
  log("Please identify which file(s) need changes based on the feedback.")
  // Read the concern body for hints
  for (const concern of concerns) {
    log(`Concern: ${concern.title}`)
    log(concern.body.substring(0, 500))
  }
  // Implement fix based on user guidance and concern content
  // (interactive -- orchestrator reads files, applies edits)
}

if (filePath) {
  // Read the target file
  const fileContent = Read(filePath)

  // Apply the fix
  // If bot provided a suggested diff, parse and apply it
  // Otherwise, interpret the concern and implement a fix
  for (const concern of concerns) {
    if (concern.hasDiff) {
      // Parse suggestion block from comment body
      // GitHub suggestion format: ```suggestion\n...\n```
      const suggestionMatch = commentBody.match(/```suggestion\n([\s\S]*?)```/)
      if (suggestionMatch && line) {
        // Apply the suggested change at the referenced line
        const suggestion = suggestionMatch[1]
        // Use Edit to apply the change
        // (the orchestrator reads context around `line` and applies the suggestion)
      }
    }
    // For non-diff concerns: interpret and fix
    // Read the surrounding code context, understand the issue, apply fix
  }
}
```

## Phase 6: Quality Checks

Run quality commands from talisman config. Uses the same pattern as arc ship quality checks.

```javascript
const qualityCommands = botReviewConfig.quality_commands ?? []

if (qualityCommands.length > 0) {
  log(`Running ${qualityCommands.length} quality check(s)...`)

  for (const cmd of qualityCommands) {
    // SEC: Validate command -- prevent injection
    // Only allow known safe executables (same pattern as ward-check.md)
    const executable = cmd.trim().split(/\s+/)[0].split('/').pop()
    const SAFE_EXECUTABLES = new Set([
      'npm', 'npx', 'yarn', 'pnpm', 'bun',
      'pytest', 'python', 'python3', 'pip',
      'cargo', 'rustfmt', 'clippy',
      'eslint', 'tsc', 'prettier',
      'ruff', 'mypy', 'black', 'isort', 'flake8',
      'go', 'golangci-lint',
      'rubocop', 'bundle',
      'git', 'make'
    ])

    if (!SAFE_EXECUTABLES.has(executable)) {
      warn(`Skipping untrusted quality command: ${cmd} (executable '${executable}' not in allowlist)`)
      continue
    }

    const result = Bash(`${cmd} 2>&1`)
    if (result.exitCode !== 0) {
      warn(`Quality check failed: ${cmd}`)
      warn(result.substring(0, 1000))

      AskUserQuestion({
        questions: [{
          question: `Quality check \`${cmd}\` failed. Continue anyway?`,
          header: "Quality Check Failed",
          options: [
            { label: "Continue", description: "Proceed despite quality check failure" },
            { label: "Abort", description: "Stop and fix manually" }
          ],
          multiSelect: false
        }]
      })

      if ($USER_RESPONSE === "Abort") {
        error("Aborted by user after quality check failure.")
        return
      }
    } else {
      log(`Quality check passed: ${cmd}`)
    }
  }
} else {
  log("No quality commands configured. Set arc.ship.bot_review.quality_commands in talisman.yml.")
}
```

## Phase 7: Commit & Push

Stage changes, commit with descriptive message, and push.

```javascript
// Stage only the modified file(s)
if (filePath) {
  Bash(`git add "${filePath}"`)
} else {
  // If multiple files were modified, stage all changes
  Bash(`git add -u`)
}

// Check if there are staged changes
const hasStagedChanges = Bash(`git diff --cached --quiet 2>/dev/null; echo $?`).trim() === "1"

if (!hasStagedChanges) {
  log("No changes to commit. Proceeding to reply.")
} else {
  const commitMsg = `fix: resolve PR comment #${commentId} from ${authorLogin}\n\nAddresses feedback on ${filePath || 'PR'}${line ? ` (line ${line})` : ''}`
  Bash(`git commit -m "${commitMsg}"`)

  // Push to current branch
  const currentBranch = Bash(`git rev-parse --abbrev-ref HEAD`).trim()
  Bash(`git push origin "${currentBranch}"`)
  log(`Pushed fix to ${currentBranch}`)
}

const commitSha = Bash(`git rev-parse --short HEAD`).trim()
```

## Phase 8: Reply to Comment

Reply to the comment with resolution details and commit SHA.

```javascript
const GH_ENV = 'GH_PROMPT_DISABLED=1'

// Phase8_FalsePositive handler
if (userChoice === "Mark as false positive") {
  const replyBody = "Thank you for the review. After verification against the actual code, this appears to be a false positive -- the concern does not apply to the current implementation."

  if (commentType === "review_comment") {
    Bash(`${GH_ENV} gh api repos/${repoOwner}/${repoName}/pulls/${prNumber}/comments/${commentId}/replies -f body="${replyBody}"`)
  } else {
    Bash(`${GH_ENV} gh api repos/${repoOwner}/${repoName}/issues/${prNumber}/comments -f body="Re: comment by @${authorLogin} -- ${replyBody}"`)
  }
  log("Replied with false positive explanation.")
}

// Phase8 handler (fix applied)
if (userChoice !== "Mark as false positive" && userChoice !== "Reply only" && userChoice !== "Skip") {
  const replyBody = hasStagedChanges
    ? `Addressed in ${commitSha}. Thank you for the review.`
    : "Reviewed and verified -- no changes needed. Thank you for the feedback."

  if (commentType === "review_comment") {
    Bash(`${GH_ENV} gh api repos/${repoOwner}/${repoName}/pulls/${prNumber}/comments/${commentId}/replies -f body="${replyBody}"`)
  } else {
    Bash(`${GH_ENV} gh api repos/${repoOwner}/${repoName}/issues/${prNumber}/comments -f body="Re: comment by @${authorLogin} -- ${replyBody}"`)
  }
  log(`Replied to comment #${commentId}`)
}

// "Reply only" handler
if (userChoice === "Reply only") {
  AskUserQuestion({
    questions: [{
      question: "What would you like to reply?",
      header: "Reply Content"
    }]
  })

  const replyBody = $USER_RESPONSE

  if (commentType === "review_comment") {
    Bash(`${GH_ENV} gh api repos/${repoOwner}/${repoName}/pulls/${prNumber}/comments/${commentId}/replies -f body="${replyBody}"`)
  } else {
    Bash(`${GH_ENV} gh api repos/${repoOwner}/${repoName}/issues/${prNumber}/comments -f body="${replyBody}"`)
  }
  log("Reply posted.")
}
```

## Phase 9: Resolve Thread

If `--resolve` flag or user chose "Fix, reply, and resolve", resolve the review thread via GraphQL.

```javascript
if (shouldResolve && commentType === "review_comment") {
  // Fetch the thread ID for this comment via GraphQL
  // CONCERN 5: owner/repo already extracted explicitly in Phase 1
  const threadQuery = `
    query($owner: String!, $repo: String!, $prNumber: Int!) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $prNumber) {
          reviewThreads(first: 100) {
            nodes {
              id
              isResolved
              comments(first: 1) {
                nodes { databaseId }
              }
            }
          }
        }
      }
    }
  `

  const threadResult = Bash(`${GH_ENV} gh api graphql -F owner="${repoOwner}" -F repo="${repoName}" -F prNumber=${prNumber} -f query='${threadQuery}'`)
  const threads = JSON.parse(threadResult)
  const targetThread = threads.data?.repository?.pullRequest?.reviewThreads?.nodes?.find(
    t => t.comments?.nodes?.[0]?.databaseId === commentId
  )

  if (targetThread && !targetThread.isResolved) {
    // Resolve the thread
    const resolveMutation = `
      mutation($threadId: ID!) {
        resolveReviewThread(input: { threadId: $threadId }) {
          thread { isResolved }
        }
      }
    `
    Bash(`${GH_ENV} gh api graphql -F threadId="${targetThread.id}" -f query='${resolveMutation}'`)
    log(`Thread resolved for comment #${commentId}`)
  } else if (targetThread?.isResolved) {
    log("Thread already resolved.")
  } else {
    warn(`Could not find review thread for comment #${commentId}. Thread may have been deleted.`)
  }
} else if (shouldResolve && commentType === "issue_comment") {
  log("Issue comments do not have review threads to resolve. Skipping thread resolution.")
}
```

## Completion Report

```
Comment #${commentId} on PR #${prNumber} has been resolved.

Author: ${authorLogin} (${isBot ? "Bot" : "Human"})
File: ${filePath || "PR-level"}
Action: ${userChoice}
Commit: ${commitSha || "N/A"}
Thread resolved: ${shouldResolve ? "Yes" : "No"}
```
