# Rune Plugin Marketplace

Plugin marketplace for [Rune](plugins/rune/) — multi-agent engineering orchestration for [Claude Code](https://claude.ai/claude-code).

## Install

```bash
claude plugin add vinhnxv/rune-plugin
```

## Plugins

| Plugin | Description | Version |
|--------|-------------|---------|
| [rune](plugins/rune/) | Multi-agent engineering orchestration — plan, work, review, audit with Agent Teams | 1.4.1 |

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
