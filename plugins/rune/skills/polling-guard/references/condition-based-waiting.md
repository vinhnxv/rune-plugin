# Condition-Based Waiting Patterns

Supplement to polling-guard skill. Covers async wait strategies and debugging
beyond standard TaskList polling loops.

## Wait-Until Patterns

Instead of fixed-interval polling, wait for a specific condition:

| Pattern | When to Use | Command |
|---------|-------------|---------|
| File appearance | Waiting for agent output file | `while [[ ! -f "$file" ]]; do sleep 1; done` |
| Process exit | Waiting for build/test process | `wait $PID; echo "exit: $?"` |
| Port availability | Waiting for service startup | `while ! nc -z localhost $PORT 2>/dev/null; do sleep 1; done` |
| Log pattern | Waiting for specific log line | `tail -f "$log" \| grep -qF -- "$PATTERN"` |
| Task completion | Standard agent monitoring | `TaskList() → check status → sleep 30 → repeat` |

**Security**: `$PATTERN` must be a literal string, not derived from untrusted external sources. `-qF` uses fixed-string matching (no regex interpretation) and `--` ends option parsing, preventing injection.

**Note**: `nc -z` behavior varies between BSD (macOS) and GNU (Linux) netcat. On some Linux systems, use `timeout 1 bash -c '</dev/tcp/localhost/$PORT'` as a portable alternative.

**Important**: File-based waiting should always have a timeout fallback:
```bash
timeout=120; elapsed=0
while [[ ! -f "$file" ]] && (( elapsed < timeout )); do
  sleep 2; elapsed=$((elapsed + 2))
done
[[ -f "$file" ]] || echo "Timeout waiting for $file"
```

## Timeout + Retry with Exponential Backoff

When polling external resources (APIs, services, CI):

```
Initial delay:  1s
Backoff factor: 2x (1s → 2s → 4s → 8s → 16s → 30s)
Max delay:      30s (cap to prevent excessive waits)
Max attempts:   10
Jitter:         ±20% (prevent thundering herd in parallel agents)
Total timeout:  ~3 minutes
```

Formula per attempt: `delay = min(initial * (factor ^ attempt) * (1 ± jitter), max_delay)`

**Note**: `^` denotes exponentiation (mathematical notation). In bash, use `bc` or Python for actual computation — bash's `^` operator is XOR.

## Deadlock Detection in Multi-Agent Workflows

Signs that an agent workflow is deadlocked:

1. **Circular dependency**: Two workers both waiting for each other's output file
   - Detection: TaskList shows both tasks `in_progress` with no file output for >2x expected duration
   - Fix: Break the cycle — one worker should produce partial output

2. **Resource starvation**: All workers blocked on the same shared resource
   - Detection: Multiple workers idle, same file appears in multiple task descriptions
   - Fix: Serialize access via task dependency ordering

3. **Silent failure**: Worker crashed without updating TaskList
   - Detection: Task `in_progress` but teammate is idle for >3 poll cycles
   - Fix: TeammateIdle hook should catch this — check `on-teammate-idle.sh` output

4. **Ghost dependency**: Task waiting on a dependency that was deleted or completed
   - Detection: Task `blockedBy` references a task ID that doesn't exist or is already `completed`
   - Fix: TaskUpdate to clear stale `blockedBy`

### Deadlock Recovery Checklist
- [ ] Check TaskList for circular `blockedBy` chains
- [ ] Check team config for idle teammates with `in_progress` tasks
- [ ] Check tmp/ for missing output files from "completed" tasks
- [ ] Check git status for uncommitted changes from crashed workers

## Polling vs Push-Based Patterns

| Pattern | Latency | Complexity | When to Use |
|---------|---------|------------|-------------|
| Fixed polling (TaskList + sleep) | Medium (up to pollInterval) | Low | Standard agent monitoring |
| File-based signals (tmp/.rune-signals/) | Low (filesystem event) | Medium | Completion detection (existing) |
| Exponential backoff | Variable | Medium | External service waiting |
| Condition-based (wait-until) | Lowest | Higher | Known specific condition |

**Default recommendation**: Use standard TaskList polling (polling-guard) for agent monitoring.
Use condition-based only for non-agent waits (services, files, processes).
