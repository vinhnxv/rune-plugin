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
 └──────────── or /rune:arc ──────────────────────────────┘
 (Forge → Plan Review → Refinement → Verification → Work → Gap Analysis → Review → Mend → Verify Mend → Audit)
```

| Command | Purpose |
|---------|---------|
| `/rune:arc` | End-to-end pipeline (forge, plan review, refinement, verification, work, gap analysis, review, mend, verify mend, audit) |
| `/rune:plan` | Turn feature ideas into structured plans with parallel research agents |
| `/rune:forge` | Deepen existing plan with Forge Gaze enrichment |
| `/rune:work` | Execute plans with self-organizing swarm workers |
| `/rune:review` | Multi-agent code review before merging |
| `/rune:mend` | Parallel finding resolution from TOME |
| `/rune:elicit` | Interactive structured reasoning (Tree of Thoughts, Pre-mortem, Red Team, 5 Whys) |
| `/rune:audit` | Full codebase audit with specialized Ashes |

Each Ash teammate gets its own 200k context window, eliminating single-context bottlenecks.

> [!WARNING]
> **Rune is a token-grinding machine.** Each workflow summons multiple agents with their own 200k context windows, consuming tokens rapidly. A single `/rune:arc` or `/rune:audit` run can burn through a significant portion of your weekly usage limit.
>
> **We recommend Claude Max ($200/month) or higher.** If you are on a lower-tier subscription, a single Rune session could exhaust your entire week's usage allowance. Use `--dry-run` to preview scope before committing to a full run.

## Learn More

- [Full component reference](plugins/rune/README.md) — all agents, commands, skills, and configuration
- [Changelog](plugins/rune/CHANGELOG.md)

## Plugins

| Plugin | Description | Version |
|--------|-------------|---------|
| [rune](plugins/rune/) | Multi-agent engineering orchestration — plan, work, review, audit with Agent Teams | 1.16.0 |

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
        ├── talisman.example.yml
        ├── CLAUDE.md
        └── README.md
```

## License

MIT
