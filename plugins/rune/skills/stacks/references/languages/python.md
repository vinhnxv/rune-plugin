# Python Patterns for Rune

## Quick Reference

| Scenario | Pattern | Severity if violated |
|----------|---------|---------------------|
| Missing type hints on public API | Add return type + param annotations | P2 |
| Bare `except:` or `except Exception:` | Catch specific exceptions | P1 |
| Mutable default argument | Use `None` + conditional | P1 |
| Missing `__slots__` on data-heavy class | Add `__slots__` or use dataclass | P3 |
| `asyncio.gather()` without `return_exceptions` | Use `TaskGroup` or `return_exceptions=True` | P2 |
| String formatting with `%` or `.format()` | Use f-strings (Python 3.6+) | P3 |

## Key Rules

### Rule 1: Type Hints (Python 3.10+)
- BAD: `def get_user(id): ...`
- GOOD: `def get_user(id: int) -> User | None: ...`
- Detection: `rg "^def \w+\([^:)]+\)" --type py` (params without type hints)

### Rule 2: Modern Union Syntax
- BAD: `Optional[str]`, `Union[str, int]`
- GOOD: `str | None`, `str | int` (Python 3.10+)
- Detection: `rg "Optional\[|Union\[" --type py`

### Rule 3: Structural Pattern Matching
- BAD: Long if/elif chains on type or value
- GOOD: `match value: case Pattern(): ...` (Python 3.10+)
- Detection: Manual review of if/elif chains > 3 branches

### Rule 4: Exception Handling
- BAD: `except:` or `except Exception:`
- GOOD: `except ValueError as e:` (specific)
- Detection: `rg "except\s*(Exception\s*)?:" --type py`

### Rule 5: Async Patterns
- BAD: `await asyncio.gather(*tasks)` without error handling
- GOOD: `async with asyncio.TaskGroup() as tg: ...` (Python 3.11+)
- Detection: `rg "asyncio\.gather" --type py`

## Anti-Patterns

| Anti-Pattern | Why It's Bad | Fix |
|-------------|-------------|-----|
| Mutable default args (`def f(x=[])`) | Shared across calls | `def f(x=None): x = x or []` |
| Global mutable state | Thread-unsafe, hard to test | Dependency injection |
| `import *` | Namespace pollution | Explicit imports |
| Nested try/except > 2 levels | Unreadable | Extract functions |
| `type: ignore` without code | Suppresses real errors | Fix the type issue or add specific ignore |

## Performance Patterns

| Pattern | When | Impact |
|---------|------|--------|
| `__slots__` | Many instances of same class | 40-50% less memory |
| `@functools.lru_cache` | Pure functions with repeated inputs | Avoid recomputation |
| `collections.deque` | FIFO/LIFO operations | O(1) vs O(n) for list.pop(0) |
| Generator expressions | Large sequences | Lazy evaluation, less memory |
| `dataclasses(slots=True)` | Data containers (3.10+) | Combines dataclass + slots |

## Security Checklist

- [ ] No `eval()` or `exec()` with user input
- [ ] No `pickle.loads()` on untrusted data
- [ ] No `subprocess.shell=True` with user input
- [ ] No `os.system()` — use `subprocess.run()` instead
- [ ] SQL queries use parameterized queries, not f-strings
- [ ] `hashlib` uses `secrets.compare_digest()` for timing-safe comparison
- [ ] No hardcoded secrets (use environment variables)

## Audit Commands

```bash
# Find functions missing type hints
rg "^def \w+\([^:)]+\)" --type py

# Find bare except clauses
rg "except\s*:" --type py

# Find mutable default arguments
rg "def \w+\(.*=\s*(\[|\{)" --type py

# Find deprecated typing imports
rg "from typing import.*(Optional|Union|List|Dict|Tuple|Set)" --type py

# Find async anti-patterns
rg "asyncio\.(gather|wait|sleep)" --type py

# Find security issues
rg "(eval|exec|pickle\.loads|os\.system)\(" --type py
```
