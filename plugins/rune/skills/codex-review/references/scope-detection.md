# Scope Detection — Phase 0

> Determines what files/content to review based on arguments and flags.
> Called from SKILL.md Phase 0.

## Parse Arguments

```javascript
const args = parseArguments($ARGUMENTS)
const flags = {
  staged: args.includes('--staged'),
  commits: extractFlag(args, '--commits'),
  prompt: extractFlag(args, '--prompt'),
  files: extractFlag(args, '--files'),
  focus: extractFlag(args, '--focus') || 'all',
  maxAgents: parseInt(extractFlag(args, '--max-agents') || '6'),
  claudeOnly: args.includes('--claude-only'),
  codexOnly: args.includes('--codex-only'),
  noCrossVerify: args.includes('--no-cross-verify'),
  reasoning: extractFlag(args, '--reasoning') || 'high'
}
const positionalArg = getPositionalArg(args)  // first non-flag argument
```

## Scope Type Detection

```
1. Check positional arg:
   a. Matches PR#<N> regex → scope_type = "pr"
   b. Exists as a file → scope_type = "files"
   c. Exists as a directory → scope_type = "directory"
2. --staged → scope_type = "staged"
3. --commits <range> → scope_type = "commits"
4. --prompt "<text>" without files → scope_type = "custom"
5. Default (no args) → scope_type = "diff"
```

## File List Assembly

| scope_type | Command |
|-----------|---------|
| `files` | Use path directly |
| `directory` | `find <dir> -type f \( -name "*.js" -o -name "*.ts" -o -name "*.py" ... \) \| grep -v node_modules \| grep -v .git` |
| `pr` | `gh pr diff <N> --name-only` |
| `staged` | `git diff --cached --name-only` |
| `commits` | `git diff <range> --name-only` |
| `diff` | `git diff --name-only` + `git diff origin/HEAD...HEAD --name-only` (union, dedup) |
| `custom` | `--files` if provided, else empty (prompt-only review) |

## Scope Validation

```
- Reject if: absolute paths, ".." traversal, paths outside project root (SEC-PATH-001)
- Warn if: total_files > 100 → "Large scope detected. Consider narrowing with --files or --focus."
- Error if: file_list is empty AND scope_type != "custom"
```
