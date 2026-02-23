# PostgreSQL Patterns for Rune

## Quick Reference

| Scenario | Pattern | Severity if violated |
|----------|---------|---------------------|
| Missing index on WHERE column | Add appropriate index type | P2 |
| Sequential scan on large table | Add index or rewrite query | P2 |
| JSONB without GIN index | Add GIN index for containment queries | P2 |
| Long-running transaction | Narrow transaction scope | P1 |
| Connection pool exhaustion | Configure pool size, add timeout | P1 |
| Migration locks table | Use concurrent operations | P1 |

## Index Strategies

| Index Type | Use Case | Example |
|-----------|----------|---------|
| B-tree (default) | Equality, range, sorting | `CREATE INDEX ON users (email)` |
| GIN | JSONB containment, full-text search, arrays | `CREATE INDEX ON docs USING GIN (metadata)` |
| GiST | Geometric, range types, nearest-neighbor | `CREATE INDEX ON locations USING GiST (coords)` |
| BRIN | Naturally ordered data (timestamps, IDs) | `CREATE INDEX ON logs USING BRIN (created_at)` |
| Hash | Equality-only (rare, B-tree usually better) | `CREATE INDEX ON cache USING HASH (key)` |
| Partial | Conditional subset | `CREATE INDEX ON orders (status) WHERE status = 'pending'` |
| Covering | Index-only scans | `CREATE INDEX ON users (email) INCLUDE (name)` |

## Key Rules

### Rule 1: JSONB Best Practices
- BAD: `SELECT * FROM docs WHERE metadata->>'type' = 'report'` (no index)
- GOOD: GIN index + containment: `WHERE metadata @> '{"type":"report"}'`
- Detection: `rg "@>|->>" --type sql` (check for GIN index existence)

### Rule 2: Advisory Locks for Concurrency
- BAD: `SELECT FOR UPDATE` on hot rows (contention)
- GOOD: `pg_advisory_xact_lock(hashtext('resource_key'))` for serialization
- Detection: `rg "FOR UPDATE|advisory_lock" --type sql --type py`

### Rule 3: CTEs and Window Functions
- BAD: Subquery in SELECT for running totals
- GOOD: `SUM(amount) OVER (ORDER BY created_at)` (window function)
- Detection: `rg "OVER\s*\(" --type sql` (verify window function usage)

### Rule 4: Connection Pooling
- BAD: New connection per request
- GOOD: PgBouncer (external) or `asyncpg` pool with `min_size`/`max_size`
- Configuration: `pool_size=20, max_overflow=10, pool_pre_ping=True`

### Rule 5: EXPLAIN ANALYZE Interpretation
- Key metrics: `actual time`, `rows`, `loops`, `Buffers: shared hit/read`
- Red flags: `Seq Scan` on large tables, `Sort Method: external merge`, `Nested Loop` with high rows
- Goal: `Index Scan` or `Index Only Scan` for filtered queries

## Migration Patterns

| Operation | Risk | Zero-Downtime Approach |
|-----------|------|----------------------|
| Add column (nullable) | Low | `ALTER TABLE ADD COLUMN ... NULL` |
| Add column (NOT NULL) | High (lock) | Add NULL → backfill → SET NOT NULL |
| Add index | High (lock) | `CREATE INDEX CONCURRENTLY` |
| Drop column | Medium | Stop reading → deploy → drop |
| Rename column | High | Add new → dual-write → migrate reads → drop old |
| Change type | High | Add new column → copy → swap |

## Performance Patterns

| Pattern | When | Impact |
|---------|------|--------|
| Partial indexes | Queries filter to subset | Smaller index, faster scans |
| Covering indexes (INCLUDE) | Frequent index-only queries | Avoids heap fetch |
| `VACUUM ANALYZE` | After bulk operations | Updated statistics for planner |
| Connection pooling | All production apps | Reduced connection overhead |
| `SET statement_timeout` | Long-running queries | Prevents runaway queries |
| Batch operations with `COPY` | Bulk inserts | 10-100x faster than INSERT |

## Security Checklist

- [ ] No superuser connections from application
- [ ] Row-level security (RLS) for multi-tenant data
- [ ] `ssl=require` on connections
- [ ] `pg_hba.conf` restricts access by IP
- [ ] No `trust` authentication method
- [ ] Parameterized queries only (no string interpolation)

## Audit Commands

```bash
# Find raw SQL queries (potential injection)
rg "execute\(\"SELECT|execute\(\"INSERT|execute\(\"UPDATE" --type py

# Find missing CONCURRENTLY on index creation
rg "CREATE INDEX" --type sql | rg -v "CONCURRENTLY"

# Find FOR UPDATE (potential contention)
rg "FOR UPDATE|FOR SHARE" --type sql --type py

# Find sequential scan hints (missing indexes)
rg "Seq Scan" --type sql

# Find connection creation without pooling
rg "psycopg2\.connect\(|asyncpg\.connect\(" --type py
```
