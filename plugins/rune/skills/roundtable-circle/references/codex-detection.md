# Codex Oracle Detection Algorithm

Canonical detection logic for the Codex Oracle built-in Ash. Used by review, audit, plan, work, and forge pipelines.

## Algorithm

```
1. Read talisman.yml (project or global)
2. If talisman.codex.disabled is true:
   - Log: "Codex Oracle: disabled via talisman.yml"
   - Skip Codex Oracle entirely
3. Otherwise, check CLI availability:
   Bash: command -v codex >/dev/null 2>&1 && echo "available" || echo "unavailable"
   - If "available":
     a. Add "codex-oracle" to the Ash selection (always-on when available, like Ward Sentinel)
     b. Log: "Codex Oracle: CLI detected, adding cross-model reviewer"
   - If "unavailable":
     a. Log: "Codex Oracle: CLI not found, skipping (install: npm install -g @openai/codex)"
4. Check jq availability (needed for JSONL parsing of Codex output):
   Bash: command -v jq >/dev/null 2>&1 && echo "available" || echo "unavailable"
   - If "unavailable":
     a. Log: "Warning: jq not found — Codex Oracle will use raw text fallback instead of JSONL parsing"
     b. Set codex_jq_available = false (Codex Oracle Ash prompt will skip jq-based parsing)
   - If "available":
     a. Set codex_jq_available = true
5. Check talisman.codex.workflows (default: [review, audit, plan, forge, work])
   - If the current workflow is NOT in the workflows list, remove codex-oracle from Ash selection
```

## Notes

- CLI detection is fast (no network call, <100ms)
- When Codex Oracle is selected, it counts toward the `max_ashes` cap
- Codex Oracle findings use the `CDX` prefix
- Findings participate in standard dedup, TOME aggregation, and Truthsight verification
- Disable entirely via `codex.disabled: true` in talisman.yml (runtime kill switch)
