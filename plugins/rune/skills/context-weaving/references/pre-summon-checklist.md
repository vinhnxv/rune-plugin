# Pre-Summon Checklist (8 Thoughts)

> Complete this checklist BEFORE summoning agents in any multi-agent workflow.

## Thought 1: Count and Estimate

```
Count the agents I'm about to summon.
Each Task return adds ~3-5k tokens without budget.
Base context (CLAUDE.md + rules + MCP) is ~30k tokens.

Agents planned: [list them]
Estimated return tokens (with budget): [count] x 150 = [total]
```

## Thought 2: Choose Strategy

```
- All Rune commands → Agent Teams + Glyph Budget + inscription.json REQUIRED.
- Custom workflows (3+ agents) → Agent Teams + Glyph Budget + inscription.json REQUIRED.

My choice: [strategy]
```

## Thought 3: Plan Output Directory

```
Where should agents write findings?
- Review: tmp/reviews/{pr-number}/
- Audit: tmp/audit/{timestamp}/
- Plan research: tmp/plans/{timestamp}/research/
- Custom: tmp/{workflow-name}/

I'll use: [directory]
Ensure directory exists: mkdir -p [directory]
```

## Thought 4: Verify Protocol Injection

```
For each agent prompt, append:
1. GLYPH BUDGET PROTOCOL (write to file, return summary only)
2. Output Requirements (required_sections from inscription)
3. Seal Format (file, sections, findings, evidence-verified, confidence)

Agents receiving the protocol:
- [agent-1]: ✓ budget + requirements + seal
- [agent-2]: ✓ budget + requirements + seal
```

## Thought 5: Post-Completion Validation

```
After all agents complete:
1. Validate against inscription:
   - Circuit breaker: ALL files missing? → systemic failure, abort
   - Per-file: each file exists AND > 100 bytes? → PASS/FAIL
   - Report gaps in TOME.md "Incomplete" section
2. Summon Runebinder if 4+ raw files
3. Run quality probes on TOME.md
```

## Thought 6: Revision Checkpoint

```
1. Can I merge redundant agents? (overlapping concerns?)
2. Should I split overloaded agents? (>30 files?)
3. Is the context budget per agent appropriate?
4. Does the inscription accurately reflect my plan?
```

## Thought 7: Fallback Strategies

```
1. Agent timeout → Mark as partial, document gap
2. Inscription validation fails → Circuit breaker for ALL missing, per-file for partial
3. Context overflow mid-orchestration → Load compression, write scratch summary
```

## Thought 8: Verification Planning

```
1. 3+ teammates with Report-format? → Enable Truthsight Layer 0
2. Review/audit workflow? → Enable Layer 2 (Smart Verifier)
3. Add verification block to inscription.json
```
