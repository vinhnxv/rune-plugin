# readTalisman() — Canonical Definition

Reads talisman configuration with project-first, global-second fallback.

## Implementation

```javascript
// readTalisman: SDK Read() with project→global fallback. See references/read-talisman.md
function readTalisman() {
  // 1. Try project-level talisman
  try {
    const content = Read(".claude/talisman.yml")
    if (content) return parseYaml(content)
  } catch (_) { /* not found — fall through */ }

  // 2. Try global talisman (CHOME pattern)
  //    SDK Read() auto-resolves CLAUDE_CONFIG_DIR and ~.
  //    NEVER use Bash("cat ~/.claude/talisman.yml") — tilde does not expand in ZSH eval.
  try {
    const globalPath = `${CLAUDE_CONFIG_DIR ?? HOME + "/.claude"}/talisman.yml`
    const content = Read(globalPath)
    if (content) return parseYaml(content)
  } catch (_) { /* not found — fall through */ }

  // 3. Empty fallback
  return {}
}
```

## Fallback Order

1. **Project**: `.claude/talisman.yml` (relative — SDK resolves to project root)
2. **Global**: `$CHOME/talisman.yml` where `CHOME="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"`
3. **Empty**: `{}` on any error (file missing, parse failure, permission denied)

## CHOME Resolution (Bash contexts only)

If you must reference the global talisman path in a Bash command (e.g., for existence checks in hook scripts), always resolve `CHOME` first:

```bash
CHOME="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
# Correct:
test -f "$CHOME/talisman.yml"
# NEVER:
test -f ~/.claude/talisman.yml    # ~ does not expand in ZSH eval
cat ~/.claude/talisman.yml        # same problem
```

## Anti-Patterns

| Pattern | Problem | Fix |
|---------|---------|-----|
| `Bash("cat ~/.claude/talisman.yml")` | `~` not expanded in ZSH eval | Use `Read(".claude/talisman.yml")` |
| `Bash("test -f ~/.claude/talisman.yml")` | Same tilde expansion bug | Use `Read()` with try/catch |
| `Bash("cat $HOME/.claude/talisman.yml")` | Works but unnecessary shell roundtrip | Use `Read()` — it's faster and safer |
| Hardcoded `~/.claude/` in any Bash context | ZSH incompatible | Use `CHOME` pattern or SDK `Read()` |

## Cross-References

- [chome-pattern skill](../skills/chome-pattern/SKILL.md) — full CLAUDE_CONFIG_DIR resolution guide
- [zsh-compat skill](../skills/zsh-compat/SKILL.md) — ZSH shell compatibility patterns
- [configuration-guide.md](configuration-guide.md) — talisman.yml schema and defaults
