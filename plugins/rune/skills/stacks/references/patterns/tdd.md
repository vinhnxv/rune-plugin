# TDD Patterns for Rune

## Quick Reference

| Scenario | Pattern | Severity if violated |
|----------|---------|---------------------|
| Feature commit without preceding test commit | Write test first (`test:` before `feat:`) | P2 |
| Test without assertion | Add meaningful assertions | P1 |
| Test naming doesn't describe behavior | Use `test_<action>_<condition>_<expected>` | P3 |
| Missing edge case tests | Cover boundaries, nulls, empty inputs | P2 |
| Test depends on execution order | Make each test independent | P1 |
| Low coverage on domain layer | Domain layer should be >90% | P2 |

## TDD Cycle

```
RED    → Write a failing test for the desired behavior
GREEN  → Write the minimum code to make the test pass
REFACTOR → Clean up without changing behavior (tests still pass)
```

**Commit order validation**: Tests should be committed before or with the implementation, never after.

## Coverage Thresholds by Layer

| Layer | Target | Rationale |
|-------|--------|-----------|
| Domain (entities, value objects) | >90% | Core business logic, highest value |
| Application (services, use cases) | >80% | Orchestration, important paths |
| Infrastructure (repos, adapters) | >60% | I/O-heavy, integration-tested |
| API (routes, controllers) | >70% | Request/response handling |

## Key Rules

### Rule 1: Test Naming Conventions

**Python (pytest)**:
```python
def test_create_user_with_valid_email_returns_success():
def test_create_user_with_duplicate_email_raises_conflict():
def test_delete_user_when_not_found_raises_not_found():
```

**TypeScript (vitest/jest)**:
```typescript
describe('UserService', () => {
  it('should create user with valid email', () => {})
  it('should throw ConflictError when email is duplicate', () => {})
})
```

**Rust**:
```rust
#[test]
fn create_user_with_valid_email_returns_ok() {}
#[test]
fn create_user_with_duplicate_email_returns_err() {}
```

### Rule 2: AAA Pattern (Arrange-Act-Assert)
```python
def test_transfer_funds_between_accounts():
    # Arrange
    sender = Account(balance=1000)
    receiver = Account(balance=500)

    # Act
    result = transfer(sender, receiver, amount=200)

    # Assert
    assert result.is_success()
    assert sender.balance == 800
    assert receiver.balance == 700
```

### Rule 3: Parameterized Tests
- BAD: Duplicate tests for each input variation
- GOOD: `@pytest.mark.parametrize` or `test.each`
```python
@pytest.mark.parametrize("email,expected", [
    ("user@example.com", True),
    ("invalid", False),
    ("", False),
    ("a@b.c", True),
])
def test_email_validation(email, expected):
    assert is_valid_email(email) == expected
```

### Rule 4: Test Independence
- BAD: Test B depends on state created by Test A
- GOOD: Each test creates its own fixtures/state
- Detection: Run tests in random order (`pytest -p randomly`)

### Rule 5: Commit Order
- BAD: `feat: add user service` → `test: add user service tests`
- GOOD: `test: add user service tests (RED)` → `feat: add user service (GREEN)` → `refactor: clean up user service`
- Detection: `git log --oneline` — check test commits precede feat commits

## Anti-Patterns

| Anti-Pattern | Why It's Bad | Fix |
|-------------|-------------|-----|
| Test without assertion | Always passes, no value | Add `assert` / `expect` |
| Testing implementation details | Brittle, breaks on refactor | Test behavior, not internals |
| Shared mutable state | Order-dependent tests | Fresh fixtures per test |
| Mock everything | Tests don't catch integration bugs | Mock only I/O boundaries |
| Testing getters/setters | No business logic tested | Test meaningful behavior |
| Single happy-path test | Misses edge cases | Add error/boundary tests |

## Edge Case Checklist

- [ ] Null/None input
- [ ] Empty string/collection
- [ ] Boundary values (0, -1, MAX_INT)
- [ ] Duplicate entries
- [ ] Concurrent access
- [ ] Unicode and special characters
- [ ] Very large input
- [ ] Permission denied / unauthorized

## Audit Commands

```bash
# Find test files
rg -l "def test_|it\(|describe\(" --type py --type ts --type rust

# Find tests without assertions
rg "def test_" --type py -A 10 | rg -v "assert|raise"

# Find test coverage gaps (files without corresponding test)
# Compare: src/services/*.py vs tests/services/test_*.py

# Check commit order (test before feat)
git log --oneline --format="%s" | head -20
```
