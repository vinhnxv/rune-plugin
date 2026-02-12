# Inscription Schema

> JSON schema for `inscription.json` — the output contract for Rune workflows.

## Complete Schema

```json
{
  "workflow": "string — rune-review | rune-audit | rune-plan | rune-work",
  "timestamp": "ISO-8601 datetime",
  "pr_number": "integer (optional — for reviews)",
  "branch": "string (optional)",
  "output_dir": "string — path to output directory",

  "teammates": [
    {
      "name": "string — tarnished role name",
      "output_file": "string — filename relative to output_dir",
      "required_sections": ["array of section header strings"],
      "role": "string — human-readable role description",
      "perspectives": ["array of embedded review perspectives"],
      "file_scope": ["array of file patterns assigned to this teammate"]
    }
  ],

  "aggregator": {
    "name": "runebinder",
    "output_file": "TOME.md"
  },

  "verification": {
    "enabled": "boolean",
    "layer_0_circuit": {
      "failure_threshold": "integer — max inline check failures before pause",
      "recovery_seconds": "integer — wait before retry"
    },
    "layer_2_circuit": {
      "failure_threshold": "integer — max hallucinated findings before flagging",
      "recovery_seconds": "integer — wait before retry"
    },
    "max_reverify_agents": "integer — max re-verify agents to spawn"
  },

  "context_engineering": {
    "read_ordering": "source_first | reference_first",
    "instruction_anchoring": "boolean — ANCHOR + RE-ANCHOR in prompts",
    "reanchor_interval": "integer — re-anchor every N files",
    "context_budget": {
      "backend": "integer — max files for backend reviewer",
      "security": "integer — max files for security reviewer",
      "frontend": "integer — max files for frontend reviewer",
      "docs": "integer — max files for docs reviewer"
    }
  }
}
```

## Example: Review Inscription

```json
{
  "workflow": "rune-review",
  "timestamp": "2026-02-11T10:30:00Z",
  "pr_number": 142,
  "branch": "feat/user-authentication",
  "output_dir": "tmp/reviews/142/",
  "teammates": [
    {
      "name": "forge-warden",
      "output_file": "forge-warden.md",
      "required_sections": ["P1 (Critical)", "P2 (High)", "P3 (Medium)", "Self-Review Log", "Summary"],
      "role": "Backend code review",
      "perspectives": ["architecture", "performance", "logic-bugs", "duplication"],
      "file_scope": ["backend/**/*.py"]
    },
    {
      "name": "ward-sentinel",
      "output_file": "ward-sentinel.md",
      "required_sections": ["P1 (Critical)", "P2 (High)", "P3 (Medium)", "Self-Review Log", "Summary"],
      "role": "Security review",
      "perspectives": ["vulnerabilities", "auth", "injection", "owasp"],
      "file_scope": ["**/*"]
    },
    {
      "name": "pattern-weaver",
      "output_file": "pattern-weaver.md",
      "required_sections": ["P1 (Critical)", "P2 (High)", "P3 (Medium)", "Self-Review Log", "Summary"],
      "role": "Quality and patterns review",
      "perspectives": ["simplicity", "tdd", "dead-code", "patterns"],
      "file_scope": ["**/*"]
    }
  ],
  "aggregator": {
    "name": "runebinder",
    "output_file": "TOME.md"
  },
  "verification": {
    "enabled": true,
    "layer_0_circuit": { "failure_threshold": 3, "recovery_seconds": 60 },
    "layer_2_circuit": { "failure_threshold": 2, "recovery_seconds": 120 },
    "max_reverify_agents": 2
  },
  "context_engineering": {
    "read_ordering": "source_first",
    "instruction_anchoring": true,
    "reanchor_interval": 5,
    "context_budget": {
      "backend": 30,
      "security": 20,
      "frontend": 25,
      "docs": 25
    }
  }
}
```

## Required Fields

| Field | Required | Default |
|-------|----------|---------|
| `workflow` | Yes | — |
| `timestamp` | Yes | — |
| `output_dir` | Yes | — |
| `teammates` | Yes | — |
| `teammates[].name` | Yes | — |
| `teammates[].output_file` | Yes | — |
| `teammates[].required_sections` | Yes | — |
| `aggregator` | No | No aggregation |
| `verification` | No | `{ "enabled": false }` |
| `context_engineering` | No | Defaults applied |
