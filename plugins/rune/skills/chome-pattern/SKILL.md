---
name: chome-pattern
description: |
  Use when a Bash command references ~/.claude/ and fails with "path not found"
  or "No such file or directory" in multi-account setups. Use when writing
  rm -rf for team or task directories, when CLAUDE_CONFIG_DIR is set to a
  custom path and SDK auto-resolution is unavailable, or when auditing commands
  for hardcoded ~/.claude/ paths. Failure scenario: rm -rf ~/.claude/teams/...
  silently targets wrong directory when CLAUDE_CONFIG_DIR is set.
  Keywords: CLAUDE_CONFIG_DIR, CHOME, ~/.claude, multi-account, config directory,
  path not found, team cleanup, hardcoded path.

  <example>
  Context: A command needs to rm-rf team directories after cleanup.
  user: "Add cleanup logic for team dirs"
  assistant: "I'll use the CHOME pattern for the rm-rf call — SDK calls like Read() auto-resolve, but Bash commands need explicit CHOME."
  <commentary>Load chome-pattern skill for correct Bash path resolution.</commentary>
  </example>

  <example>
  Context: Auditing a new command for hardcoded ~/.claude/ references.
  user: "Check if this command works with custom config dirs"
  assistant: "I'll classify each ~/.claude/ reference as SDK (safe) or Bash (needs CHOME)..."
  <commentary>CHOME skill provides the classification framework.</commentary>
  </example>
user-invocable: false
allowed-tools:
  - Read
  - Glob
  - Grep
---

# CHOME Pattern — Multi-Account Config Directory Resolution

## Problem

Claude Code supports custom config directories via `CLAUDE_CONFIG_DIR` environment variable. Users with multiple accounts (work/personal) set this to different paths:

```bash
# Default
~/.claude/

# Custom (work account)
CLAUDE_CONFIG_DIR=~/.claude-work

# Custom (personal)
CLAUDE_CONFIG_DIR=~/.claude-personal
```

When code hardcodes `~/.claude/`, it breaks on custom setups — rm-rf deletes the wrong dir, find scans the wrong path, test checks the wrong location.

## The Rule: SDK vs Bash

### Specialized SDK calls — SAFE, auto-resolve internally

These tools manage config dirs internally and always resolve `CLAUDE_CONFIG_DIR`:

| Tool | Example | Safe? |
|------|---------|-------|
| `TeamCreate()` | `TeamCreate({ team_name: "my-team" })` | Yes |
| `TeamDelete()` | `TeamDelete()` | Yes |
| `TaskList()` | `TaskList()` | Yes |
| `SendMessage()` | `SendMessage({ type: "message", ... })` | Yes |

### Generic file tools + Bash — MUST use CHOME

`Read()`, `Write()`, `Glob()` are generic file tools — they read/write the exact path you give them.
`Bash()` executes shell commands literally. Neither auto-resolves `CLAUDE_CONFIG_DIR`:

| Tool | Example | Safe? |
|------|---------|-------|
| `Read(\`~/.claude/...\`)` | Reads wrong dir if CLAUDE_CONFIG_DIR set | **NO** |
| `Write(\`~/.claude/...\`)` | Writes wrong dir | **NO** |
| `Glob("~/.claude/...")` | Scans wrong dir | **NO** |
| `Bash("rm -rf ...")` | Deletes wrong dir | **NO** |
| `Bash("find ...")` | Scans wrong dir | **NO** |
| `Bash("test -d ...")` | Checks wrong dir | **NO** |

## Canonical Patterns

### Pattern 1: Inline CHOME (most common)

For single Bash calls, inline the CHOME resolution:

```javascript
// rm-rf with CHOME
Bash(`CHOME="\${CLAUDE_CONFIG_DIR:-$HOME/.claude}" && rm -rf "$CHOME/teams/${teamName}/" "$CHOME/tasks/${teamName}/" 2>/dev/null`)

// find with CHOME
Bash(`CHOME="\${CLAUDE_CONFIG_DIR:-$HOME/.claude}" && find "$CHOME/teams/" -maxdepth 1 -type d \( -name "rune-*" -o -name "arc-*" \) -exec rm -rf {} + 2>/dev/null`)

// test -f with CHOME (post-create verification)
Bash(`CHOME="\${CLAUDE_CONFIG_DIR:-$HOME/.claude}" && test -f "$CHOME/teams/${teamName}/config.json" || echo "WARN: config.json not found"`)

// test -d with CHOME (directory existence check)
Bash(`CHOME="\${CLAUDE_CONFIG_DIR:-$HOME/.claude}" && test -d "$CHOME/teams/${teamName}/" && echo "exists"`)
```

### Pattern 2: Resolved CHOME variable (for multiple Bash calls)

When a command makes several Bash calls to config dirs, resolve CHOME once at the top:

```javascript
// Resolve once at command start
const CHOME = Bash(`echo "\${CLAUDE_CONFIG_DIR:-$HOME/.claude}"`).trim()

// Then use in multiple Bash calls
Bash(`find "${CHOME}/teams" -mindepth 1 -maxdepth 1 -type d 2>/dev/null`)
Bash(`test -d "${CHOME}/teams" && echo ok 2>/dev/null`)
Bash(`rm -rf "${CHOME}/teams/${teamName}/" "${CHOME}/tasks/${teamName}/" 2>/dev/null`)
```

### Pattern 3: Documentation references

In markdown docs, tables, and comments that describe paths for humans:

```markdown
<!-- Option A: Use $CHOME notation (preferred for pseudocode docs) -->
| Team config | `$CHOME/teams/{name}/config.json` |

<!-- Option B: Use ~/.claude/ with a note (preferred for user-facing docs) -->
| Team config | `~/.claude/teams/{name}/` (or `$CLAUDE_CONFIG_DIR/teams/` if set) |
```

## Classification Checklist

When auditing a file for hardcoded `~/.claude/`, classify each reference:

| Context | Action |
|---------|--------|
| Inside `Bash(...)` | **FIX** — use CHOME pattern |
| Inside `Read(...)` | **FIX** — resolve CHOME first, pass `${CHOME}/teams/...` |
| Inside `Write(...)` | **FIX** — resolve CHOME first, pass `${CHOME}/...` |
| Inside `Glob(...)` | **FIX** — resolve CHOME first, pass `${CHOME}/...` |
| In `TeamCreate/TeamDelete/TaskList` | **SAFE** — specialized SDK, auto-resolves |
| In markdown table | **OPTIONAL** — add `(or $CLAUDE_CONFIG_DIR if set)` note |
| In YAML comment | **SAFE** — user docs, no code execution |
| In CHANGELOG | **SAFE** — historical record |

## Session Identity Triplet

CHOME resolves **installation isolation** (which Claude Code config dir). Two additional fields complete the session identity triplet for **session isolation**:

| Field | Source | Isolation Layer |
|-------|--------|----------------|
| `config_dir` | `CHOME` (resolved `CLAUDE_CONFIG_DIR`) | Installation — different Claude Code configs |
| `owner_pid` | `$PPID` in Bash | Session — different sessions with same config |
| `session_id` | `CLAUDE_SESSION_ID` / `${CLAUDE_SESSION_ID}` in skills | Diagnostic — correlation across hooks and logs |

All Rune state files must include all three fields. See `team-lifecycle-guard.md` for the full ownership verification matrix.

## Security: Always Quote CHOME

The CHOME variable MUST be double-quoted in all Bash contexts to prevent word splitting:

```javascript
// CORRECT — quoted
Bash(`rm -rf "$CHOME/teams/${name}/"`)

// WRONG — unquoted, breaks on paths with spaces
Bash(`rm -rf $CHOME/teams/${name}/`)
```

## Anti-Patterns

### exists() with bare path

```javascript
// WRONG — exists() is not an SDK call, it's a pseudocode helper
if (exists(`~/.claude/teams/${name}/`)) { ... }

// CORRECT — use Bash test with CHOME
const result = Bash(`CHOME="\${CLAUDE_CONFIG_DIR:-$HOME/.claude}" && test -d "$CHOME/teams/${name}/" && echo "exists"`)
if (result.trim() === "exists") { ... }
```

### Read/Bash with bare ~/.claude/ path

```javascript
// WRONG — Read is a generic file tool, does NOT auto-resolve CLAUDE_CONFIG_DIR
const config = Read(`~/.claude/teams/${name}/config.json`)

// WRONG — Bash does NOT auto-resolve either
Bash(`rm -rf ~/.claude/teams/${name}/`)  // BUG: wrong dir on custom setups

// CORRECT — resolve CHOME once, use for both Read and Bash
const CHOME = Bash(`echo "\${CLAUDE_CONFIG_DIR:-$HOME/.claude}"`).trim()
const config = Read(`${CHOME}/teams/${name}/config.json`)
Bash(`rm -rf "${CHOME}/teams/${name}/"`)
```

## Grep Audit Commands

To find all `~/.claude/` references in a project:

```bash
# All references
rg '~/\.claude/' plugins/rune/

# Only Bash-context (dangerous)
rg 'Bash\(.*~/\.claude/' plugins/rune/

# rm-rf/find/test/ls in shell context
rg 'rm -rf ~/\.claude/|find ~/\.claude/|test -d ~/\.claude/|ls ~/\.claude/' plugins/rune/

# exists() with bare path (pseudocode anti-pattern)
rg 'exists\(.*~/\.claude/' plugins/rune/
```
