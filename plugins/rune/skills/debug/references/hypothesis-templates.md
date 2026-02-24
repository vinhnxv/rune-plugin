# Hypothesis Templates by Failure Category

Reference document for the `/rune:debug` TRIAGE phase. Use these templates to generate
3-5 competing hypotheses based on the classified failure category.

## Template Format

Each hypothesis must be:
- **Testable**: Can be confirmed or falsified with available tools
- **Falsifiable**: There exists evidence that would disprove it
- **Specific**: Points to a concrete cause, not a vague area

---

## REGRESSION (H-REG)

**Trigger**: `git log` shows activity within 5 commits + failure is deterministic.

| ID | Template | Investigation Approach |
|----|----------|----------------------|
| H-REG-001 | Commit `{hash}` changed `{file}` which broke `{failing_test/behavior}` | `git bisect`, `git diff {hash}~1 {hash}`, read changed lines |
| H-REG-002 | Merge of branch `{branch}` introduced conflicting changes in `{module}` | `git log --merges`, check merge resolution in affected files |
| H-REG-003 | Dependency update in `{lockfile}` changed behavior of `{function}` | `git diff {hash} -- {lockfile}`, check dep changelogs |
| H-REG-004 | Refactoring in `{file}` missed a call site at `{location}` | `grep -rn {old_name}`, check all references |

**Disproof strategy**: Revert the suspected commit — if failure persists, hypothesis is refuted.

---

## ENVIRONMENT (H-ENV)

**Trigger**: Error contains "not found", "permission denied", "timeout", or "works locally".

| ID | Template | Investigation Approach |
|----|----------|----------------------|
| H-ENV-001 | Missing binary/tool `{name}` in `$PATH` on this environment | `which {name}`, `command -v {name}`, check CI Dockerfile |
| H-ENV-002 | File permission mismatch: `{file}` not executable/readable | `ls -la {file}`, `stat {file}` |
| H-ENV-003 | Environment variable `{VAR}` not set or has unexpected value | `echo "$VAR"`, check .env/.envrc files |
| H-ENV-004 | Version mismatch: `{tool}` is version `{actual}` but requires `{expected}` | `{tool} --version`, check version constraints |

**Disproof strategy**: Set up identical environment conditions — if failure doesn't reproduce, hypothesis is refuted.

---

## DATA/FIXTURE (H-DATA)

**Trigger**: Failures non-deterministic across runs, uses DB fixtures, or data layer in stack trace.

| ID | Template | Investigation Approach |
|----|----------|----------------------|
| H-DATA-001 | Test fixture `{fixture}` has stale/invalid data for `{field}` | Read fixture file, compare against schema |
| H-DATA-002 | Database migration `{migration}` left schema in inconsistent state | Check migration history, run `db:migrate:status` |
| H-DATA-003 | Input data `{source}` contains unexpected format/encoding | Read data source, check encoding headers |
| H-DATA-004 | Shared test state: test `{A}` modifies data that test `{B}` depends on | Run tests in isolation, check for global state |

**Disproof strategy**: Run with fresh/known-good data — if failure persists, hypothesis is refuted.

---

## LOGIC ERROR (H-LOGIC)

**Trigger**: Error deterministic, stack trace points to application code, isolatable to specific function.

| ID | Template | Investigation Approach |
|----|----------|----------------------|
| H-LOGIC-001 | Off-by-one error in `{function}` at `{file:line}` | Read function, trace boundary conditions |
| H-LOGIC-002 | Missing null/undefined check before accessing `{property}` | Read call chain, check all callers |
| H-LOGIC-003 | Incorrect conditional logic: `{condition}` should be `{corrected}` | Read condition, test with edge cases |
| H-LOGIC-004 | Wrong variable used: `{actual}` instead of `{expected}` at `{location}` | Read scope, check variable names/types |
| H-LOGIC-005 | Type coercion issue: `{value}` treated as `{wrong_type}` | Check type assertions, compare expected vs actual |

**Disproof strategy**: Add assertion at suspected location — if assertion never fires, hypothesis is refuted.

---

## INTEGRATION (H-INT)

**Trigger**: Stack trace spans two modules, involves serialization, or manifests at API boundary.

| ID | Template | Investigation Approach |
|----|----------|----------------------|
| H-INT-001 | Module `{A}` sends `{format}` but module `{B}` expects `{other_format}` | Read both interfaces, compare schemas |
| H-INT-002 | API contract change: `{endpoint}` response shape changed without client update | Check API types, response serializers, client parsers |
| H-INT-003 | Import resolution: `{module}` resolves to wrong version/file | Check import paths, module resolution config |
| H-INT-004 | Serialization mismatch: `{field}` serialized as `{type_a}` but deserialized as `{type_b}` | Trace data through serialization boundary |

**Disproof strategy**: Test modules in isolation — if both pass independently, integration is the issue. If one fails alone, it's a LOGIC error.

---

## CONCURRENCY (H-CONC)

**Trigger**: Failure intermittent (<100% of runs), codebase has async code or shared mutable state.

| ID | Template | Investigation Approach |
|----|----------|----------------------|
| H-CONC-001 | Race condition between `{operation_A}` and `{operation_B}` on `{shared_resource}` | Check for unprotected shared state, add timing logs |
| H-CONC-002 | Deadlock: `{lock_A}` and `{lock_B}` acquired in inconsistent order | Trace lock acquisition paths, check ordering |
| H-CONC-003 | Async operation `{op}` completes after dependent code already executed | Check await/callback ordering, race with Promise.all |
| H-CONC-004 | File contention: multiple processes writing to `{file}` simultaneously | Check for `.lock` files, file open modes, PID checks |

**Disproof strategy**: Serialize operations — if failure disappears under serial execution, concurrency is confirmed.

---

## Generating Hypotheses from Error Output

When generating hypotheses in the TRIAGE phase:

1. **Classify** the failure using the trigger heuristics above
2. **Select** the matching category template
3. **Fill in** template variables from the actual error output
4. **Generate 3-5 hypotheses** — at least one from a different category than the primary
5. **Rank** by specificity (most specific = easiest to falsify = investigate first)

### Mixed-Category Strategy

Always include at least one hypothesis from a different category than the primary classification.
This guards against misclassification:
- If classified LOGIC, include one REGRESSION hypothesis (is it a recent change?)
- If classified ENVIRONMENT, include one LOGIC hypothesis (is the code wrong?)
- If classified DATA, include one INTEGRATION hypothesis (is the boundary wrong?)
