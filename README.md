# Rune Marketplace

A Claude Code plugin marketplace featuring **Rune** — multi-agent engineering orchestration that plans, works, reviews, and audits with Agent Teams.

## Claude Code Install

```bash
/plugin marketplace add https://github.com/vinhnxv/rune-plugin
/plugin install rune
```

## Workflow

```
Plan → Work → Review → Mend → Audit
 └──────────── or /rune:arc ──────────────┘
 (Forge → Plan Review → Work → Review → Mend → Audit)
```

| Command | Purpose |
|---------|---------|
| `/rune:arc` | End-to-end pipeline (forge, plan review, work, review, mend, audit) |
| `/rune:plan` | Turn feature ideas into structured plans with parallel research agents |
| `/rune:work` | Execute plans with self-organizing swarm workers |
| `/rune:review` | Multi-agent code review before merging |
| `/rune:mend` | Parallel finding resolution from TOME |
| `/rune:audit` | Full codebase audit with specialized Ashes |

Each Ash teammate gets its own 200k context window, eliminating single-context bottlenecks.

## Learn More

- [Full component reference](plugins/rune/README.md) — all agents, commands, skills, and configuration
- [Changelog](plugins/rune/CHANGELOG.md)

## Plugins

| Plugin | Description | Version |
|--------|-------------|---------|
| [rune](plugins/rune/) | Multi-agent engineering orchestration — plan, work, review, audit with Agent Teams | 1.10.0 |

## Structure

```
rune-plugin/
├── .claude-plugin/
│   └── marketplace.json
└── plugins/
    └── rune/              # Main plugin
        ├── .claude-plugin/
        │   └── plugin.json
        ├── agents/
        ├── commands/
        ├── skills/
        ├── docs/
        ├── CLAUDE.md
        └── README.md
```

## License

MIT
