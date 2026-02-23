# SQLAlchemy Patterns for Rune

## Quick Reference

| Scenario | Pattern | Severity if violated |
|----------|---------|---------------------|
| N+1 query in relationship access | Use `joinedload()` or `selectinload()` | P2 |
| Unbounded query (no LIMIT) | Add `.limit()` or pagination | P2 |
| Missing index on filtered column | Add `Index()` to model | P2 |
| Session leak (no close/context manager) | Use `async with` or `yield` dependency | P1 |
| Transaction boundary too wide | Narrow `commit()` scope | P2 |
| Blocking call in async session | Use `run_sync()` or async methods | P1 |

## Key Rules

### Rule 1: Eager Loading (SQL-PERF-001)
- BAD: `for user in users: user.posts` (lazy load = N+1)
- GOOD: `select(User).options(selectinload(User.posts))`
- Detection: `rg "\.options\(" --type py` (check for missing eager load on queries with loops)

### Rule 2: Unbounded Queries (SQL-PERF-002)
- BAD: `session.execute(select(User))` without limit
- GOOD: `session.execute(select(User).limit(100).offset(0))`
- Detection: `rg "select\(" --type py | rg -v "\.limit\("` in repository files

### Rule 3: Missing Index (SQL-PERF-003)
- BAD: `Column(String)` used in `WHERE` clause without index
- GOOD: `Column(String, index=True)` or `Index('ix_users_email', 'email')`
- Detection: Cross-reference `rg "\.where\(|\.filter\(" --type py` with model index definitions

### Rule 4: Async Session Management
- BAD: `session = AsyncSession(engine)` without close
- GOOD: `async with async_session() as session:` (context manager)
- Detection: `rg "AsyncSession\(" --type py` (check for context manager usage)

### Rule 5: Transaction Boundaries
- BAD: Single transaction spanning multiple service operations
- GOOD: Explicit `async with session.begin():` per logical unit
- Detection: Manual review of `commit()` placement

## Anti-Patterns

| Anti-Pattern | Why It's Bad | Fix |
|-------------|-------------|-----|
| `session.execute(text("SELECT..."))` | SQL injection if interpolated | Use `text().bindparams()` |
| Lazy loading in async | Raises `MissingGreenlet` | Eager load or `run_sync()` |
| `Session()` without engine dispose | Connection leak | Use `create_async_engine()` + dispose |
| `expire_on_commit=True` (default) | Extra queries after commit | Set `False` for read-heavy patterns |
| Models as API response | Tight coupling | Map to Pydantic schemas |

## Performance Patterns

| Pattern | When | Impact |
|---------|------|--------|
| `selectinload()` | One-to-many relations | 2 queries (no JOIN bloat) |
| `joinedload()` | One-to-one or many-to-one | Single query with JOIN |
| `subqueryload()` | Large result sets with relations | Separate subquery per relation |
| `.execution_options(yield_per=N)` | Processing large datasets | Streaming results |
| Connection pooling | All production deployments | Fewer connection creation overhead |
| `Insert().values([...])` | Batch inserts | Single roundtrip vs N inserts |

## Security Checklist

- [ ] No `text()` with string formatting (use `bindparams()`)
- [ ] All sessions use context managers (no leak)
- [ ] Engine URL not hardcoded (use env vars)
- [ ] `pool_pre_ping=True` for connection health checks
- [ ] Sensitive columns have appropriate types (e.g., `LargeBinary` for encrypted data)

## Migration Safety

| Risk | Pattern | Mitigation |
|------|---------|------------|
| Table lock on ALTER | `ADD COLUMN NOT NULL` | `ADD COLUMN NULL` → backfill → `ALTER NOT NULL` |
| Long-running migration | Data transformation in migration | Separate migration from backfill script |
| Irreversible migration | `DROP COLUMN` | Keep downgrade path or mark as irreversible |
| Type change | `ALTER COLUMN TYPE` | Create new column → copy → rename |

## Audit Commands

```bash
# Find N+1 risks (queries without eager loading)
rg "session\.(execute|scalars)\(" --type py | rg -v "options\("

# Find unbounded queries
rg "\.execute\(select\(" --type py | rg -v "\.limit\("

# Find raw SQL
rg "text\(\"" --type py

# Find session creation without context manager
rg "AsyncSession\(" --type py

# Find missing indexes
rg "Column\(" --type py | rg "String|Integer" | rg -v "index=True|primary_key"

# Find blocking calls in async context
rg "session\.execute\(" --type py | rg -v "await"
```
