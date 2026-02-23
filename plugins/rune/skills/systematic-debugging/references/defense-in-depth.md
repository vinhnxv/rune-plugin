# Defense-in-Depth — Multi-Layer Validation Strategy

After fixing a bug, add defensive layers at the failure point to prevent regression.
Apply these layers in order — each builds on the previous.

## Layer 1: Input Validation (Boundary Defense)

**Goal**: Reject invalid data before it reaches internal logic.

**When to apply**: At every external boundary — user input, API responses, file reads,
inter-agent messages, task descriptions.

**Pattern**:
```python
def process_task(task_id: str) -> None:
    # Validate at the boundary
    if not task_id or not task_id.isdigit():
        raise ValueError(f"Invalid task_id: {task_id!r} — expected numeric string")
    ...
```

**Questions to ask**:
- Where does the bad data enter the system?
- What types are valid? What ranges? What formats?
- Can I fail fast here rather than deep inside the logic?

---

## Layer 2: Assertions (Invariant Defense)

**Goal**: Crash loudly when assumptions are violated, not silently corrupt data.

**When to apply**: At internal boundaries where invariants must hold — after transformation,
before mutation, at state transitions.

**Pattern**:
```python
def merge_results(results: list[dict]) -> dict:
    merged = _do_merge(results)
    # Assert the invariant that merge guarantees
    assert "status" in merged, f"Merge lost status field: {merged}"
    assert merged["status"] in VALID_STATUSES, f"Invalid status: {merged['status']}"
    return merged
```

**Questions to ask**:
- What must be true at this point in the code?
- If this invariant breaks, what downstream failures would it cause?
- Is this assertion cheap enough to leave in production? (If not, use logging)

---

## Layer 3: Error Handling (Graceful Degradation)

**Goal**: When failure occurs, degrade gracefully — not silently, not catastrophically.

**When to apply**: At integration points — external calls, file I/O, subprocesses, IPC.

**Anti-pattern** (exception swallowing):
```python
try:
    result = run_ward_check()
except Exception:
    pass  # NEVER do this — hides the failure
```

**Pattern** (explicit degradation with logging):
```python
try:
    result = run_ward_check()
except WardCheckError as e:
    log.error(f"Ward check failed: {e}")
    # Escalate with context — do not silently proceed
    raise TaskBlockedError(f"Ward failure: {e}") from e
```

**Questions to ask**:
- What should happen when this fails? Retry? Escalate? Abort?
- Does the caller need to know this failed?
- Am I preserving the original exception context (`from e`)?

---

## Layer 4: Monitoring (Observability)

**Goal**: Make failures visible before users (or agents) notice them.

**When to apply**: At key checkpoints in long-running workflows, after state transitions,
around external dependencies.

**Pattern for Rune agents**:
```
# In Seal messages — include diagnostic signals:
Seal: task #5 done. Files: src/auth.py. Tests: 12/12.
Confidence: 85. Inner-flame: pass. Revised: 2.
Ward-output: "ruff: 0 errors, mypy: 0 errors"
```

**What to log**:
- Input → output summary (not full content)
- Duration for slow operations
- Confidence scores and revision counts
- Any unexpected branches taken (fallbacks, retries)

---

## Layer 5: Tests (Regression Prevention)

**Goal**: Ensure the specific failure mode can never silently regress.

**When to apply**: After EVERY bug fix — write the test that would have caught the bug.

**Pattern**:
```python
def test_merge_preserves_status_field():
    """Regression: merge() was dropping status field when results list was empty."""
    result = merge_results([])
    assert "status" in result, "Empty merge must produce status field"
    assert result["status"] == "empty"
```

**Test naming convention**:
- `test_{function}_regression_{what_broke}` — for regression tests
- `test_{function}_boundary_{condition}` — for boundary tests added post-fix

**Questions to ask**:
- If I revert my fix, does this test fail? (It should)
- Does this test name explain WHAT failed and WHY?
- Is this test deterministic? (No flakiness)

---

## Applying All 5 Layers After a Bug Fix

Checklist after fixing any bug:

```
[ ] Layer 1: Added input validation at the entry point where bad data entered?
[ ] Layer 2: Added assertion at the invariant that was violated?
[ ] Layer 3: Error handling gracefully degrades (no silent swallow)?
[ ] Layer 4: Added observable signal (log/Seal field) at the failure point?
[ ] Layer 5: Test written that fails without the fix and passes with it?
```

Not every fix requires all 5 layers. Apply the layers relevant to the failure:
- **Data corruption bugs**: Layers 1 + 2 + 5
- **Silent failures**: Layers 3 + 4 + 5
- **Regression bugs**: Layer 5 (always), then consider 1-4
- **Integration failures**: Layers 3 + 4 + 5
