# Wisdom Protocol — 6-Step for Wisdom Sage

The Wisdom Sage investigates the **WHY** behind code: design intent, historical context, and caution zones.

## Prerequisites

Input from prior phases:
- MUST-CHANGE and SHOULD-CHECK findings from Impact Layer (with file:line references)
- risk-map.json from Lore Layer (for risk tier context)

## Step 1: IDENTIFY

Receive MUST-CHANGE and SHOULD-CHECK findings from Impact Layer.

```
For each finding:
  - Record file path and line range
  - Record confidence and classification
  - Record risk tier from Lore (if available)
```

**Cap**: Investigate at most 20 findings (configurable via `goldmask.layers.wisdom.max_findings_to_investigate`). Prioritize MUST-CHANGE over SHOULD-CHECK. Within same classification, prioritize by confidence descending.

## Step 2: BLAME

Run `git blame` on affected lines to find original authors and commit hashes.

```bash
# Validate line range is numeric before interpolation
[[ "${start}" =~ ^[0-9]+$ ]] && [[ "${end}" =~ ^[0-9]+$ ]] || { echo "Invalid line range"; exit 1; }

# Use --porcelain for machine-parseable output (10-50x less output than --line-porcelain)
git blame --porcelain -L "${start},${end}" -w -- "${file}"

# -w: ignore whitespace changes (surface the semantic author)
# -L: target specific lines (not the whole file)
# --: separates options from file path (prevents flag injection via filename)
```

### Parsing Porcelain Output

```
{commit_hash} {orig_line} {final_line} {num_lines}
author {name}
author-mail <{email}>
author-time {unix_timestamp}
author-tz {timezone}
committer {name}
...
summary {commit message first line}
filename {path}
\t{line content}
```

Key fields to extract:
- `commit_hash` — for Step 3 context lookup
- `author` + `author-time` — for age and contributor analysis
- `summary` — for intent signal matching

### Edge Cases

- **Shallow clones**: Check `git rev-parse --is-shallow-repository`. If `true`, degrade to current-state-only analysis (comments and code patterns, no history).
- **Renamed files**: Blame follows renames by default. Use `git log --follow -- {file}` only if blame returns a single bulk commit (likely a rename).
- **Binary files**: Blame produces no output. Skip.

## Step 3: CONTEXT

Read commit messages for the hashes found in Step 2.

```bash
# Get full commit message (not just first line)
git show --no-patch --format="%B" {commit_hash}
```

Look for WHY signals, not just WHAT:
- "because..." / "in order to..." / "to prevent..."
- Issue/PR references (#123, JIRA-456)
- ADR references
- "workaround for..." / "temporary until..."

### No Commit Messages

If commits have no useful context (e.g., "update", "fix", "wip"), record this absence. The finding gets UNKNOWN intent, which still has a default caution score of 0.40.

## Step 4: COMMENTS

Read surrounding code comments, docstrings, and TODO markers.

```bash
# Read file context around the blamed lines (5 lines before/after)
# Look for:
#   - Inline comments (// or #)
#   - Block comments (/* ... */)
#   - Docstrings (""" ... """ or /** ... */)
#   - TODO/FIXME/HACK/XXX markers
#   - Warning comments ("DO NOT", "IMPORTANT", "NOTE")
```

### Comment Indicators

| Indicator | Maps To | Example |
|-----------|---------|---------|
| `TODO` with reason | Caution modifier +0.05 | `# TODO: replace with proper mutex after v3 migration` |
| `HACK`/`FIXME`/`XXX` | WORKAROUND intent | `// HACK: sleep to avoid race condition` |
| `DO NOT REMOVE`/`IMPORTANT` | Warning modifier +0.10 | `# DO NOT REMOVE: prevents double-charging` |
| Spec reference | CONSTRAINT intent | `# Per RFC 7519 section 4.1.3` |
| Performance note | OPTIMIZATION intent | `# Batched to avoid N+1 query — see benchmark PR #42` |

## Step 5: INTENT

Classify the design intent using signals from Steps 2-4.

Apply regex patterns from `intent-signals.md` against:
1. Commit message (from Step 3)
2. Code comments (from Step 4)
3. Blame summary line (from Step 2)

**Priority**: If multiple categories match, use this precedence:
```
CONSTRAINT > DEFENSIVE > WORKAROUND > COMPATIBILITY > OPTIMIZATION > CONVENTION > EXPLORATORY > UNKNOWN
```

Rationale: Safety-critical intents (CONSTRAINT, DEFENSIVE) take precedence because they carry the highest risk if violated.

## Step 6: CAUTION

Compute caution score using the formula from `confidence-scoring.md`.

```
caution = base + age_modifier + contributor_modifier + comment_modifier
caution = min(1.0, caution)
```

Gather modifier inputs:
- `code_age_days` — from blame author-time
- `distinct_authors` — count unique authors from blame
- `author_still_active` — check if author has commits in last 90 days: `git log --oneline --author="{name}" --since="90 days ago" -1` (sanitize `{name}`: strip shell metacharacters `$\`` before interpolation)
- `has_warning_comments` — from Step 4 analysis
- `has_todo_with_reason` — from Step 4 analysis

### Output

Write structured wisdom output to `{output_dir}/wisdom-report.md`:

```markdown
# Wisdom Report

## WISDOM-{NNN}: {file}:{line_range}

**Design Intent**: {category}
**Caution Score**: {0.XX} / 1.0
**Caution Level**: {CRITICAL | HIGH | MEDIUM | LOW}

**Historical Context**:
- Written by: {author} on {date} ({N days ago})
- Commit: `{hash}` -- "{commit_message_first_line}"
- Full commit context: "{relevant excerpt explaining WHY}"
- Contributors since: {N distinct authors}
- Last major change: {date} by {author} -- "{message}"

**Design Intent Evidence**:
- Commit message says: "{quote the WHY part}"
- Code comment at line {N}: "{quote the comment}"
- {Additional evidence}

**Caution Advisory**:
> {Plain English explanation of why this area needs careful modification}

**For the engineer making changes**:
1. Read commit {hash} fully before modifying
2. {Specific advice based on intent category}
3. {Verification step}
```
