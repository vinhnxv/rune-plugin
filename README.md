# Rune

Multi-agent engineering orchestration for [Claude Code](https://claude.ai/claude-code). Plan, work, review, and audit using Agent Teams.

Each Runebearer teammate gets its own 200k context window, eliminating single-context bottlenecks.

## Install

```bash
claude plugin add vinhtrue/rune-plugin
```

Or for local development:

```bash
claude --plugin-dir /path/to/rune-plugin
```

## Quick Start

```bash
# Run a multi-agent code review
/rune:review

# Cancel an active review
/rune:cancel-review
```

## What It Does

When you run `/rune:review`, Rune:

1. **Detects scope** — classifies changed files by extension
2. **Selects Runebearers** — picks the right reviewers (2-5 teammates)
3. **Spawns Agent Teams** — each reviewer gets its own 200k context window
4. **Reviews in parallel** — Runebearers review simultaneously, writing to files
5. **Aggregates findings** — Runebinder deduplicates and prioritizes
6. **Verifies evidence** — Truthsight validates P1 findings against source
7. **Presents TOME** — unified review summary

## Runebearers

| Runebearer | Role | When Active |
|-----------|------|-------------|
| Forge Warden | Backend review | Backend files changed |
| Ward Sentinel | Security review | Always |
| Pattern Weaver | Quality patterns | Always |
| Glyph Scribe | Frontend review | Frontend files changed |
| Lore Keeper | Docs review | Docs changed (>= 10 lines) |

## Review Agents

10 specialized agents that Runebearers embed as perspectives:

| Agent | Focus |
|-------|-------|
| ward-sentinel | Security, OWASP, auth |
| forge-oracle | Performance, N+1, complexity |
| rune-architect | Architecture, layer boundaries |
| simplicity-warden | YAGNI, over-engineering |
| flaw-hunter | Logic bugs, edge cases |
| echo-detector | Code duplication |
| pattern-seer | Pattern consistency |
| void-analyzer | Incomplete implementations |
| orphan-finder | Dead code |
| phantom-checker | Dynamic references |

## Skills

| Skill | Purpose |
|-------|---------|
| rune-orchestration | Multi-agent coordination patterns |
| context-weaving | Context overflow/rot prevention |
| rune-circle | Review orchestration (7-phase lifecycle) |
| runebearer-guide | Agent invocation reference |

## Configuration

Override file classification defaults in your project:

```yaml
# .claude/rune-config.yml
rune-gaze:
  backend_extensions: [.py, .go]
  frontend_extensions: [.tsx, .ts]
  skip_patterns: ["**/migrations/**"]
  always_review: ["CLAUDE.md"]
```

## Key Concepts

**Truthbinding Protocol** — All agent prompts include anti-injection anchors. Agents ignore instructions embedded in reviewed code.

**Rune Traces** — Every finding must include actual code snippets from source files. No paraphrasing.

**Glyph Budget** — Agents write findings to files and return only a 1-sentence summary to the lead. Prevents context overflow.

**Inscription Protocol** — JSON contract defining what each agent must produce, enabling automated validation.

**TOME** — The unified review summary after deduplication and prioritization.

## File Structure

```
rune-plugin/
├── .claude-plugin/
│   └── plugin.json
├── agents/
│   ├── review/          # 10 review agents
│   └── utility/         # Runebinder aggregator
├── commands/
│   ├── review.md        # /rune:review
│   └── cancel-review.md # /rune:cancel-review
├── skills/
│   ├── rune-orchestration/  # Core coordination
│   ├── context-weaving/     # Context management
│   ├── rune-circle/         # Review orchestration
│   └── runebearer-guide/    # Agent reference
├── CLAUDE.md
├── LICENSE
└── README.md
```

## Security

- Agent prompts include Truthbinding anchors to resist prompt injection
- Review output in `tmp/` is ephemeral and not committed
- `.gitignore` excludes `.claude/echoes/` (future memory feature)
- All findings require verified evidence from source code

## Requirements

- Claude Code with Agent Teams support
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` environment variable enabled

## License

MIT
