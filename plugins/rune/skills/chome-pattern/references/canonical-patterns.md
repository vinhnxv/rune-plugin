# Canonical CHOME Patterns

Three patterns for resolving CLAUDE_CONFIG_DIR in different contexts, with code examples.

**Inputs**: `CLAUDE_CONFIG_DIR` environment variable (may be unset)
**Outputs**: Correctly resolved config directory path
**Preconditions**: Understanding of SDK vs Bash tool resolution differences

## Pattern 1: Inline CHOME (most common)

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

## Pattern 2: Resolved CHOME variable (for multiple Bash calls)

When a command makes several Bash calls to config dirs, resolve CHOME once at the top:

```javascript
// Resolve once at command start
const CHOME = Bash(`echo "\${CLAUDE_CONFIG_DIR:-$HOME/.claude}"`).trim()

// Then use in multiple Bash calls
Bash(`find "${CHOME}/teams" -mindepth 1 -maxdepth 1 -type d 2>/dev/null`)
Bash(`test -d "${CHOME}/teams" && echo ok 2>/dev/null`)
Bash(`rm -rf "${CHOME}/teams/${teamName}/" "${CHOME}/tasks/${teamName}/" 2>/dev/null`)
```

## Pattern 3: Documentation references

In markdown docs, tables, and comments that describe paths for humans:

```markdown
<!-- Option A: Use $CHOME notation (preferred for pseudocode docs) -->
| Team config | `$CHOME/teams/{name}/config.json` |

<!-- Option B: Use ~/.claude/ with a note (preferred for user-facing docs) -->
| Team config | `~/.claude/teams/{name}/` (or `$CLAUDE_CONFIG_DIR/teams/` if set) |
```
