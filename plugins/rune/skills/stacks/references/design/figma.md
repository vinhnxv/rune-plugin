---
stack: figma
category: design
detection:
  manifest_files: [".figmarc", "figma.config.js"]
  env_vars: ["FIGMA_TOKEN", "FIGMA_ACCESS_TOKEN"]
  mcp_tools: ["figma_fetch_design", "figma_inspect_node"]
context_skills: ["design-sync", "figma-to-react", "frontend-design-patterns"]
review_agents: ["design-implementation-reviewer"]
---

# Figma Design Integration

## Detection Signals

Figma integration is detected through multiple independent signals:

| Signal Type | Detection | Confidence |
|-------------|-----------|-----------|
| Config file | `.figmarc` or `figma.config.js` in repo root | High |
| Env vars | `FIGMA_TOKEN` or `FIGMA_ACCESS_TOKEN` set | Medium |
| MCP tools | `figma_fetch_design`, `figma_inspect_node` available | High |
| Dependencies | `@figma/*` or `figma-api` in `package.json` | High |

**Precedence**: MCP tool availability > config file > dependency > env var.

When any signal is detected, `"figma"` is added to `detected_stack.frameworks`.

## Context Injection

When Figma is detected, the following skills are auto-loaded:

1. **design-sync** — Full Figma-to-code pipeline (VSM extraction, fidelity scoring, iterative refinement)
2. **figma-to-react** — Component translation patterns (Figma nodes to React component hierarchy)
3. **frontend-design-patterns** — Design system patterns, tokens, accessibility, responsive layout

### Design Context Document (DCD)

When `tmp/arc/{id}/design/dcd.md` or `tmp/design/dcd.md` exists, inject as additional context for:
- Implementation workers (strive phase)
- Review agents (roundtable circle)
- Gap analysis (inspect phase)

### Visual Structure Map (VSM)

When `tmp/arc/{id}/vsm/` directory has files, design verification agents receive:
- Component hierarchy from VSM
- Spacing/color token mappings
- Responsive breakpoint definitions

## Review Agent Selection

When Figma is detected, `design-implementation-reviewer` is added to specialist selections with:
- **Activation**: `detected_stack.frameworks.includes('figma') || vsm_files_exist`
- **Scope priority**: `.tsx` > `.jsx` > `.css` > `.scss` > component files
- **Perspective**: Design fidelity, token usage, responsive compliance, accessibility
