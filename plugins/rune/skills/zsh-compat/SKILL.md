---
name: zsh-compat
description: |
  Use when generating Bash commands on macOS, when ZSH-001 hook denies a command,
  when "read-only variable", "no matches found", or "command not found: !" errors
  appear in shell output, or when writing for loops over glob patterns. Covers
  read-only variables (status, pipestatus, ERRNO), glob NOMATCH protection,
  history expansion of `!` before `[[`, word splitting, and array indexing.
  Keywords: zsh, NOMATCH, status variable, read-only, nullglob, glob, ZSH-001,
  history expansion, command not found.

  <example>
  Context: LLM generating a Bash command with a loop over glob pattern.
  user: (internal — about to write shell code)
  assistant: "Using (N) qualifier on the glob for zsh safety."
  <commentary>zsh-compat ensures safe glob patterns in generated code.</commentary>
  </example>

  <example>
  Context: ZSH-001 hook denied a command.
  user: (internal — hook denied status= assignment)
  assistant: "Renaming to task_status per zsh-compat guidance."
  <commentary>zsh-compat explains why ZSH-001 fires and the correct alternative.</commentary>
  </example>
user-invocable: false
allowed-tools:
  - Read
  - Glob
  - Grep
---

# zsh Compatibility — Shell Pitfalls Reference

Claude Code's `Bash` tool inherits the user's shell. On macOS (default since Catalina), that shell is **zsh**. Many common bash patterns silently break in zsh. This reference covers the most dangerous differences.

## Enforcement

The `enforce-zsh-compat.sh` PreToolUse hook (ZSH-001) catches five common issues at runtime:
- **Check A**: Bare `status=` variable assignment → denied
- **Check B**: Unprotected glob in `for ... in GLOB; do` → auto-fixed with `setopt nullglob`
- **Check C**: `! [[ ... ]]` history expansion → auto-fixed by rewriting to `[[ ! ... ]]`
- **Check D**: `\!=` escaped not-equal in `[[ ]]` conditions → auto-fixed by stripping backslash
- **Check E**: Unprotected globs in command arguments (rm, ls, cp, etc.) → auto-fixed with `setopt nullglob`

This skill teaches the correct patterns so the hook rarely fires.

## Pitfall 1: Read-Only Variables

zsh reserves several variable names as **read-only built-ins**. Assigning to them is a fatal error.

| Variable | zsh meaning | Error message |
|----------|-------------|---------------|
| `status` | Last exit code (`$?`) | `read-only variable: status` |
| `pipestatus` | Pipeline exit codes | `read-only variable: pipestatus` |
| `ERRNO` | System errno value | `read-only variable: ERRNO` |
| `signals` | Signal name array | `read-only variable: signals` |

### Fix

Rename the variable. Use descriptive compound names:

```bash
# BAD — fatal in zsh
status=$(jq -r '.status' "$f")

# GOOD — compound name, clear intent
task_status=$(jq -r '.status' "$f")
wf_status=$(jq -r '.status' "$f")
completion_status=$(curl -s "$url")
tstat=$(grep -c 'done' "$f")
```

## Pitfall 2: Glob NOMATCH

In bash, when a glob matches **no files**, it's passed through as a literal string. In zsh, the `NOMATCH` option (on by default) makes this a **fatal error**.

```bash
# BAD — fatal in zsh if no *.md files exist
for f in tmp/reviews/*.md; do
  echo "$f"
done
# zsh: no matches found: tmp/reviews/*.md

# BAD — same issue with command arguments
ls tmp/reviews/*-verdict.md 2>/dev/null
# zsh: no matches found: tmp/reviews/*-verdict.md (2>/dev/null doesn't help!)
```

### Fix — Three Options

**Option 1: `(N)` qualifier (preferred)** — zsh-native, scoped to one glob:
```bash
for f in tmp/reviews/*.md(N); do
  echo "$f"
done
# If no matches: loop body never executes (safe)
```

**Option 2: `setopt nullglob`** — affects all subsequent globs in the script:
```bash
setopt nullglob
for f in tmp/reviews/*.md; do
  echo "$f"
done
```

**Option 3: Existence check first** — most portable:
```bash
if [ -n "$(ls tmp/reviews/*.md 2>/dev/null)" ]; then
  for f in tmp/reviews/*.md; do
    echo "$f"
  done
fi
```

### Important: `2>/dev/null` Does NOT Help

In zsh, the NOMATCH error happens **before** the command runs — it's a glob expansion error at parse time, not a command error at runtime. Redirecting stderr does not suppress it.

## Pitfall 3: Word Splitting

In bash, unquoted variables are split on `$IFS` (spaces, tabs, newlines). In zsh, **unquoted variables are NOT split** by default.

```bash
files="file1.txt file2.txt file3.txt"

# In bash: loops 3 times (word splitting)
# In zsh: loops 1 time (no word splitting — treats as single string)
for f in $files; do
  echo "$f"
done
```

### Fix

Use arrays instead of space-separated strings:
```bash
files=(file1.txt file2.txt file3.txt)
for f in "${files[@]}"; do
  echo "$f"
done
```

## Pitfall 4: Array Indexing

| Shell | First element | Array declaration |
|-------|--------------|-------------------|
| bash | `${arr[0]}` | `arr=(a b c)` |
| zsh | `${arr[1]}` | `arr=(a b c)` |

### Fix

Avoid index-based access. Use `"${arr[@]}"` for iteration (works in both).

## Pitfall 5: `=` Filename Expansion

In zsh, `=command` expands to the full path of the command. This can break commands that use `=` in unexpected positions.

```bash
# Potentially surprising in zsh:
echo =ls
# zsh outputs: /bin/ls
```

This rarely affects generated code but can cause confusion in path handling.

## Pitfall 6: `!` History Expansion Before `[[`

In zsh, `!` at the start of a command is interpreted as **history expansion** (like `!!` or `!$`). When used for logical negation before `[[ ]]`, it causes `command not found: !`.

```bash
# BAD — zsh interprets `!` as history expansion
if ! [[ "$epoch" =~ ^[0-9]+$ ]]; then
  echo "not numeric"
fi
# zsh: (eval):1: command not found: !

# GOOD — negation inside [[ ]] (semantically equivalent for single expressions)
if [[ ! "$epoch" =~ ^[0-9]+$ ]]; then
  echo "not numeric"
fi
```

### Why This Happens

In bash, `!` before `[[ ]]` is recognized as the pipeline negation operator. In zsh's eval context (which is how Claude Code's Bash tool executes commands), `!` can trigger history expansion before the parser reaches `[[`.

### Fix

Move the `!` inside `[[ ]]`. For single-expression conditionals, `! [[ expr ]]` and `[[ ! expr ]]` are semantically equivalent.

**Note**: `! command` (e.g., `! grep -q pattern file`) is generally safe because the command name that follows is a real command. The issue is specifically `! [[` where zsh gets confused.

## Pitfall 7: Escaped Not-Equal `\!=` in Conditions

In bash, `\!=` inside `[[ ]]` is valid — the backslash is silently ignored. In zsh, `[[ ]]` rejects it.

```bash
# BAD — fatal in zsh
if [[ "$owner" \!= "$session" ]]; then
  echo "mismatch"
fi
# zsh: (eval):1: condition expected: \!=

# GOOD — plain != works in both
if [[ "$owner" != "$session" ]]; then
  echo "mismatch"
fi
```

### Why This Happens

LLMs trained primarily on bash examples sometimes emit `\!=` as a "safe" form of `!=`. In bash, the backslash is a no-op before `!=` inside `[[ ]]`. In zsh, `[[ ]]` has its own parser that doesn't accept the escaped form.

## Pitfall 8: Unprotected Globs in Command Arguments

The NOMATCH issue (Pitfall 2) isn't limited to `for` loops. **Any** unmatched glob in zsh causes a fatal error — including in command arguments.

```bash
# BAD — fatal in zsh if no rune-* dirs exist
rm -rf "$CHOME/teams/rune-"* "$CHOME/tasks/rune-"* 2>/dev/null
# zsh: no matches found: /Users/me/.claude/teams/rune-*
# NOTE: 2>/dev/null does NOT help — the error is at parse time!

# GOOD — Option 1: use find (avoids shell globbing entirely)
find "$CHOME/teams/" -maxdepth 1 -type d -name "rune-*" -exec rm -rf {} + 2>/dev/null

# GOOD — Option 2: protect with nullglob
setopt nullglob; rm -rf "$CHOME/teams/rune-"* "$CHOME/tasks/rune-"* 2>/dev/null
```

### Fix — Recommended Approaches

**For cleanup commands**: Prefer `find` over shell globs. `find -name "rune-*"` passes the pattern as a string argument — no shell expansion occurs.

**For quick one-liners**: Prepend `setopt nullglob;` to the command. This is scoped to the single Bash invocation.

## Quick Reference — Safe Patterns

| Pattern | Bash-only | zsh-safe |
|---------|-----------|----------|
| Variable name | `status=val` | `task_status=val` |
| Glob loop | `for f in *.md; do` | `for f in *.md(N); do` |
| Negated `[[` | `if ! [[ expr ]]; then` | `if [[ ! expr ]]; then` |
| Word split | `for w in $var; do` | `for w in ${(s: :)var}; do` or use arrays |
| Array index | `${arr[0]}` | `${arr[1]}` or iterate with `[@]` |
| Glob in args | `rm path/*` | `setopt nullglob; rm path/*` or use `find` |
| Escaped `!=` | `[[ "$a" \!= "$b" ]]` | `[[ "$a" != "$b" ]]` |

## When This Matters Most

- **Multi-agent workflows**: LLM-generated Bash runs unsupervised on the user's shell
- **Monitoring loops**: Frequently iterate over tmp/ directories that may be empty
- **State file parsing**: Reading `.rune-*.json` files that may not exist yet
- **Review/audit output**: Checking verdict files that haven't been written yet

## See Also

- CLAUDE.md Rule #8 — inline zsh compatibility rule
- `enforce-zsh-compat.sh` — ZSH-001 PreToolUse enforcement hook
- `polling-guard` skill — monitoring loop fidelity (orthogonal but often co-occurs)
