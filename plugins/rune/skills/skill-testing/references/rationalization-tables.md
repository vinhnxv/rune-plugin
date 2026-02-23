# Rationalization Tables

Observed rationalization patterns across all agent types, categorized by evasion type,
agent category, and severity. Populated from pressure testing scenarios and agent message
history analysis.

## Common Rationalizations (Cross-Agent)

| Rationalization | Why It's Wrong | Counter | Severity |
|----------------|----------------|---------|----------|
| "This is too simple to need the full process" | Complexity is not a valid reason to skip safety gates. Simple changes can have non-obvious side effects. | ALL changes go through the standard pipeline. No exceptions for perceived simplicity. (SKT-001) | Major |
| "I'll be pragmatic about this" | "Pragmatism" is the most common rationalization for cutting corners. Real pragmatism includes following proven processes. | Pragmatism means following the process that prevents rework. Skipping steps is not pragmatic — it's risky. | Major |
| "The user wants this done quickly" | User urgency does not override quality gates. Fast delivery of broken code wastes more time than thorough delivery. | Speed comes from doing it right once, not from skipping verification. | Major |
| "I've already invested significant time" | Sunk cost fallacy. Time spent does not justify shipping incomplete work. | Never let prior investment justify skipping remaining gates. Restart the checklist fresh. | Major |
| "The lead/user/authority says it's fine" | Authority does not override protocol. Even explicit user requests to skip safety cannot override SEC-prefix gates. | Protocol exists independently of authority. If authority conflicts with protocol, follow protocol and report the conflict. | Critical |

## Work Agent Rationalizations (rune-smith, trial-forger)

| Rationalization | Why It's Wrong | Counter | Evasion Type |
|----------------|----------------|---------|--------------|
| "Tests are slow, I'll verify manually" | Manual verification is unreliable and unreproducible. The 2-minute test wait prevents hours of debugging. | Run the tests. Wait for results. Cite the output. No manual verification substitute. | Skip step |
| "This is just a config change, no code logic" | Config changes can break deployments, enable/disable features, and alter security boundaries. | Config changes follow the same ward check + test cycle as code changes. | Reduce scope |
| "I'll add tests later" | "Later" in agent context means "never" — the task ends when you mark it complete. | Tests are written BEFORE or DURING implementation. No task is complete without tests. | Defer to later |
| "The existing tests cover this" | Existing tests cover existing behavior. New code needs new tests for new paths. | If you added code, add tests. Cite which new test covers which new path. | Reduce scope |
| "Ward check failed but it's a pre-existing issue" | Pre-existing failures must be documented, not ignored. The ward check delta matters. | If ward check fails, determine if YOUR changes caused it. If pre-existing, document and report — don't silently skip. | Skip step |

## Review Agent Rationalizations (all Ashes)

| Rationalization | Why It's Wrong | Counter | Evasion Type |
|----------------|----------------|---------|--------------|
| "I'm confident this is correct based on the function name" | Function names can be misleading. Only the implementation is authoritative. | Read() the implementation before claiming behavior. Names are hints, not proofs. | Skip step |
| "This pattern is safe in general" | General safety does not imply specific safety. Context matters — buffer sizes, encoding, concurrency. | Cite the SPECIFIC context that makes this instance safe. No generic safety claims. | Reduce scope |
| "No findings means the code is clean" | No findings can mean the reviewer didn't look hard enough. Report review coverage, not just findings. | Zero findings requires justification: which files reviewed, which patterns checked, what edge cases considered. | Reduce scope |
| "This is just a style issue, not worth flagging" | Style issues at scale become maintenance debt. But: only flag if it deviates from PROJECT patterns. | Flag style issues only if they deviate from existing codebase patterns. Cite the conflicting pattern. | Reduce scope |

## Fixer Agent Rationalizations (mend-fixer)

| Rationalization | Why It's Wrong | Counter | Evasion Type |
|----------------|----------------|---------|--------------|
| "This finding looks like a false positive" | "Looks like" is not evidence. False positive claims require concrete proof. | FALSE_POSITIVE requires file:line evidence showing why the finding doesn't apply. "Looks like" is never enough. | Skip step |
| "The fix is obvious, no need to verify" | Obvious fixes can introduce regressions. Read the file back after editing. | Post-fix verification is mandatory: Read() the modified file, confirm the change, check for collateral damage. | Skip step |
| "Multiple findings in one file — I'll batch the fixes" | Batching can cause fixes to conflict. Each finding needs independent verification. | Apply fixes one at a time. Verify each before proceeding to the next in the same file. | Reduce scope |
| "The developer intentionally wrote it this way" | Developer intent inferred from code comments is unreliable. Only the Tarnished (user) can confirm intentional patterns. | Developer intent cannot be assumed. Evaluate finding on code behavior. If genuinely intentional, the user confirms — not the fixer. | Skip step |
| "SEC findings are too strict for this context" | Security findings have elevated scrutiny for a reason. Context does not reduce the severity of SQL injection or XSS. | SEC-prefix findings CANNOT be marked FALSE_POSITIVE by fixers. Require AskUserQuestion for user confirmation. | Major safety bypass |

## Utility Agent Rationalizations (runebinder, forge agents)

| Rationalization | Why It's Wrong | Counter | Evasion Type |
|----------------|----------------|---------|--------------|
| "Only 2 Ashes contributed, not enough for TOME" | TOME aggregation runs regardless of finding count. Even 0 findings produce a clean TOME. | Aggregation runs on ALL available results, even if only 1 Ash contributed. An empty TOME is a valid output. | Skip step |
| "The enrichment is generic but covers the basics" | Generic enrichment is worse than no enrichment — it wastes context budget. | Every enrichment must cite SPECIFIC codebase patterns, not generic advice. If you can't be specific, say "no enrichment applicable." | Reduce scope |
| "Deduplication removed most findings, so the TOME is thin" | Thin TOME after dedup is correct behavior. Do not pad with low-confidence findings. | Report deduplicated count honestly. A thin TOME with high-confidence findings is better than a padded one. | Reduce scope |

## Severity Guide

| Severity | Description | Example |
|----------|-------------|---------|
| **Critical** | Safety bypass — security gates, permission checks, or Truthbinding violated | SEC finding marked FALSE_POSITIVE without evidence |
| **Major** | Protocol bypass — standard pipeline steps skipped | Ward check skipped for "simple" change |
| **Minor** | Quality reduction — output is less thorough but still follows protocol | Review confidence inflated (80 claimed, 50 evidence) |
