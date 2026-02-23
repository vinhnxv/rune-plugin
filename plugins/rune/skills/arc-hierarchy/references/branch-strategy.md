# Branch Strategy Reference

Git branch management pseudocode for the `arc-hierarchy` skill. Covers feature branch creation, child branch lifecycle, merge, and cleanup.

---

## Branch Name Validation

All branch names MUST be validated before shell interpolation (SEC-2).

```javascript
// Allowlist: alphanumeric, dot, slash, hyphen, underscore — must start with alphanumeric
const BRANCH_NAME_PATTERN = /^[a-zA-Z0-9][a-zA-Z0-9._\/-]*$/

function validateBranchName(name) {
  if (!name || typeof name !== "string") {
    return { valid: false, reason: "Branch name must be a non-empty string" }
  }
  if (name.length > 200) {
    return { valid: false, reason: "Branch name too long (max 200 chars)" }
  }
  if (!BRANCH_NAME_PATTERN.test(name)) {
    return { valid: false, reason: `Branch name "${name}" contains disallowed characters` }
  }
  // Let git validate the rest (ref format compliance)
  const gitCheck = Bash(`git check-ref-format "refs/heads/${name}" 2>&1 && echo "ok" || echo "invalid"`)
  if (gitCheck.trim() !== "ok") {
    return { valid: false, reason: `git check-ref-format rejected branch name: ${name}` }
  }
  return { valid: true }
}
```

---

## createFeatureBranch(parentTitle)

Create a `feat/{sanitized-title}` branch from `main`. Used as the integration branch for all child plan changes.

**Inputs**: `parentTitle` — string from plan frontmatter `title` field or plan filename
**Outputs**: `featureBranchName: string`
**Error handling**: Throws if git operations fail or branch name invalid (SEC-2).

```javascript
function createFeatureBranch(parentTitle) {
  // Sanitize title → branch-safe slug
  const slug = parentTitle
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')   // non-alphanumeric → hyphen
    .replace(/^-+|-+$/g, '')        // strip leading/trailing hyphens
    .slice(0, 50)                   // cap length for readability

  const featureBranch = `feat/${slug}`

  // SEC-2: validate before shell interpolation
  const validation = validateBranchName(featureBranch)
  if (!validation.valid) {
    throw new Error(`Cannot create feature branch: ${validation.reason}`)
  }

  // Ensure we're on main and up to date
  const currentBranch = Bash(`git rev-parse --abbrev-ref HEAD`).trim()
  if (currentBranch !== "main" && currentBranch !== "master") {
    warn(`Not on main (currently: ${currentBranch}). Switching to main before creating feature branch.`)
    Bash(`git checkout main`)
    Bash(`git pull --ff-only origin main`)
  } else {
    Bash(`git pull --ff-only origin main`)
  }

  // Create feature branch
  const exists = Bash(`git show-ref --verify --quiet "refs/heads/${featureBranch}" 2>/dev/null && echo "yes" || echo "no"`).trim()
  if (exists === "yes") {
    warn(`Feature branch "${featureBranch}" already exists. Switching to it.`)
    Bash(`git checkout "${featureBranch}"`)
  } else {
    Bash(`git checkout -b "${featureBranch}"`)
    log(`Created feature branch: ${featureBranch}`)
  }

  return featureBranch
}
```

---

## createChildBranch(featureBranch, childSeq, childName)

Create a child branch off the feature branch for isolated child plan execution.

**Inputs**:
- `featureBranch` — validated feature branch name (e.g., `feat/user-auth`)
- `childSeq` — sequence string (e.g., `"01"`, `"02"`)
- `childName` — child plan name (e.g., `"data-layer-plan"`)

**Outputs**: `childBranchName: string`
**Error handling**: Throws if validation fails (SEC-2).

```javascript
function createChildBranch(featureBranch, childSeq, childName) {
  // Sanitize child name
  const sanitizedName = childName
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 40)

  const childBranch = `${featureBranch}/child-${childSeq}-${sanitizedName}`

  // SEC-2: validate full branch name before interpolation
  const validation = validateBranchName(childBranch)
  if (!validation.valid) {
    throw new Error(`Cannot create child branch: ${validation.reason}`)
  }

  // Switch to feature branch, then create child branch
  Bash(`git checkout "${featureBranch}"`)

  const exists = Bash(`git show-ref --verify --quiet "refs/heads/${childBranch}" 2>/dev/null && echo "yes" || echo "no"`).trim()
  if (exists === "yes") {
    warn(`Child branch "${childBranch}" already exists. Switching to it.`)
    Bash(`git checkout "${childBranch}"`)
  } else {
    Bash(`git checkout -b "${childBranch}"`)
    log(`Created child branch: ${childBranch}`)
  }

  return childBranch
}
```

---

## mergeChildToFeature(childBranch, featureBranch)

Merge child branch into feature branch using `--no-ff` for a traceable merge commit. Includes conflict resolution strategies.

**Inputs**:
- `childBranch` — validated child branch name
- `featureBranch` — validated feature branch name

**Outputs**: `{ success: boolean, conflicts?: string[] }`
**Error handling**: On conflict, pauses and asks user for resolution strategy.

```javascript
function mergeChildToFeature(childBranch, featureBranch) {
  // Switch to feature branch
  Bash(`git checkout "${featureBranch}"`)

  // Attempt merge with --no-ff for traceable history
  const mergeResult = Bash(`git merge --no-ff "${childBranch}" -m "merge: child ${childBranch}" 2>&1`)

  if (mergeResult.exitCode === 0) {
    log(`Merged ${childBranch} → ${featureBranch}`)
    return { success: true }
  }

  // Handle conflicts
  const conflictedFiles = Bash(`git diff --name-only --diff-filter=U 2>/dev/null`).trim().split("\n").filter(Boolean)

  if (conflictedFiles.length > 0) {
    warn(`Merge conflict in ${conflictedFiles.length} file(s):`)
    for (const f of conflictedFiles) {
      warn(`  ${f}`)
    }

    const resolution = AskUserQuestion({
      questions: [{
        question: `Conflict merging ${childBranch} into ${featureBranch}. How to resolve?`,
        header: "Merge Conflict",
        options: [
          { label: "Pause — I'll resolve manually", description: "Git merge state left for manual resolution" },
          { label: "Child wins", description: "Accept child branch version for all conflicts (ours=feature, theirs=child)" },
          { label: "Feature wins", description: "Accept feature branch version for all conflicts" },
          { label: "Abort merge", description: "git merge --abort and continue to next child" }
        ],
        multiSelect: false
      }]
    })

    if (resolution === "Child wins") {
      Bash(`git checkout --theirs -- ${conflictedFiles.map(f => `"${f}"`).join(" ")}`)
      Bash(`git add ${conflictedFiles.map(f => `"${f}"`).join(" ")}`)
      Bash(`git merge --continue --no-edit`)
      return { success: true, conflicts: conflictedFiles }
    } else if (resolution === "Feature wins") {
      Bash(`git checkout --ours -- ${conflictedFiles.map(f => `"${f}"`).join(" ")}`)
      Bash(`git add ${conflictedFiles.map(f => `"${f}"`).join(" ")}`)
      Bash(`git merge --continue --no-edit`)
      return { success: true, conflicts: conflictedFiles }
    } else if (resolution === "Abort merge") {
      Bash(`git merge --abort`)
      return { success: false, conflicts: conflictedFiles }
    }
    // Pause — return and let user resolve manually
    return { success: false, conflicts: conflictedFiles }
  }

  return { success: false }
}
```

---

## finalizeFeatureBranch(featureBranch)

Finalize the feature branch after all children have completed. Syncs with main, runs integration checks, and creates a PR.

**Inputs**: `featureBranch` — validated feature branch name
**Outputs**: `{ prUrl?: string, success: boolean }`
**Error handling**: Warns on rebase failure and offers alternatives. PR creation failure is non-blocking.

```javascript
function finalizeFeatureBranch(featureBranch) {
  Bash(`git checkout "${featureBranch}"`)

  // Sync with main (rebase for clean history)
  const rebaseResult = Bash(`git fetch origin main && git rebase origin/main 2>&1`)
  if (rebaseResult.exitCode !== 0) {
    warn("Rebase onto main failed. Attempting merge sync instead.")
    Bash(`git rebase --abort 2>/dev/null`)
    const mergeResult = Bash(`git merge origin/main --no-edit 2>&1`)
    if (mergeResult.exitCode !== 0) {
      warn("Could not sync with main. Feature branch may have conflicts.")
    }
  }

  // Push feature branch
  Bash(`git push origin "${featureBranch}" --force-with-lease`)

  // Create PR via gh CLI
  const ghAvailable = Bash(`which gh 2>/dev/null && echo "yes" || echo "no"`).trim()
  if (ghAvailable === "yes") {
    const prResult = Bash(`gh pr create --head "${featureBranch}" --base main --title "feat: hierarchy execution complete" --body "All child plans executed successfully via /rune:arc-hierarchy." 2>&1`)
    const prUrl = prResult.stdout.match(/https:\/\/github\.com\/[^\s]+/)?.[0]
    if (prUrl) {
      log(`PR created: ${prUrl}`)
      return { success: true, prUrl }
    }
  }

  log(`Feature branch ready: ${featureBranch}`)
  return { success: true }
}
```

---

## cleanupChildBranches(featureBranch)

Delete child branches after successful merge. Controlled by talisman configuration.

**Inputs**: `featureBranch` — validated feature branch name
**Outputs**: `void`
**Error handling**: Individual branch deletion failures are non-blocking.

```javascript
function cleanupChildBranches(featureBranch) {
  // readTalisman: SDK Read() with project→global fallback (see chome-pattern skill)
  const talisman = readTalisman()
  const cleanupEnabled = talisman?.arc_hierarchy?.cleanup_child_branches !== false  // default: true

  if (!cleanupEnabled) {
    log("Child branch cleanup disabled via talisman.arc_hierarchy.cleanup_child_branches: false")
    return
  }

  // Find all child branches for this feature
  // SEC-2: featureBranch already validated — safe to interpolate
  const branches = Bash(`git branch --list "${featureBranch}/child-*" 2>/dev/null`).trim().split("\n").filter(Boolean)

  for (const branch of branches) {
    const branchName = branch.trim().replace(/^\*\s+/, '')
    // Re-validate each branch name before deletion
    const validation = validateBranchName(branchName)
    if (!validation.valid) {
      warn(`Skipping cleanup of invalid branch name: ${branchName}`)
      continue
    }
    const deleteResult = Bash(`git branch -d "${branchName}" 2>&1`)
    if (deleteResult.exitCode !== 0) {
      warn(`Could not delete child branch "${branchName}" (may have unmerged changes)`)
    } else {
      log(`Deleted child branch: ${branchName}`)
    }
  }
}
```
