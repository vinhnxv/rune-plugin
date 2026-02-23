# MySQL Patterns for Rune

## Quick Reference

| Scenario | Pattern | Severity if violated |
|----------|---------|---------------------|
| Wrong charset (not utf8mb4) | Set `DEFAULT CHARSET=utf8mb4` | P2 |
| Deadlock-prone transaction order | Consistent lock ordering | P1 |
| Missing index on JOIN column | Add index | P2 |
| Large ALTER TABLE on production | Use `pt-online-schema-change` or online DDL | P1 |
| Implicit type conversion in WHERE | Match column types | P2 |
| No connection pooling | Configure pool (ProxySQL or app-level) | P2 |

## Key Rules

### Rule 1: Charset and Collation
- BAD: `CREATE TABLE users (...) CHARSET=utf8` (3-byte, no emoji)
- GOOD: `CREATE TABLE users (...) CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci`
- Detection: `rg "utf8[^m]|latin1" --type sql`

### Rule 2: Deadlock Prevention
- BAD: Transaction A locks row 1 then row 2; Transaction B locks row 2 then row 1
- GOOD: Always lock rows in consistent order (e.g., by primary key ascending)
- Detection: Review transaction code for inconsistent lock ordering

### Rule 3: Index Cardinality
- BAD: Index on low-cardinality column (`status ENUM('active','inactive')`)
- GOOD: Composite index with high-cardinality column first
- Detection: `SHOW INDEX FROM table_name` — check cardinality values

### Rule 4: Partition Pruning
- BAD: Query doesn't include partition key in WHERE clause
- GOOD: Always include partition key for partition elimination
- Detection: `EXPLAIN` shows `partitions: ALL` (bad) vs specific partitions (good)

### Rule 5: Online DDL
- BAD: `ALTER TABLE large_table ADD COLUMN ...` (locks table)
- GOOD: `ALTER TABLE ... ADD COLUMN ..., ALGORITHM=INPLACE, LOCK=NONE`
- Alternative: `pt-online-schema-change` for complex alterations
- Detection: Review migration files for ALTER on large tables

## Anti-Patterns

| Anti-Pattern | Why It's Bad | Fix |
|-------------|-------------|-----|
| `SELECT *` | Unnecessary data transfer | Select specific columns |
| `ORDER BY RAND()` | Full table scan + sort | Application-side random or `TABLESAMPLE` |
| Implicit type conversion | Index bypass | Match column types in WHERE |
| `LIKE '%search%'` | No index usage | Full-text search or prefix LIKE |
| Gap locks in REPEATABLE READ | Deadlocks on INSERT | Use READ COMMITTED where safe |

## Migration Patterns

| Operation | Risk | Safe Approach |
|-----------|------|---------------|
| Add column (nullable) | Low with InnoDB online DDL | `ALTER TABLE ... ADD COLUMN ... NULL, ALGORITHM=INPLACE` |
| Add column (NOT NULL + default) | Medium | MySQL 8.0+ instant ADD COLUMN; older: pt-osc |
| Add index | Low | `ALTER TABLE ... ADD INDEX ..., ALGORITHM=INPLACE, LOCK=NONE` |
| Drop column | Medium | `pt-online-schema-change` on large tables |
| Change column type | High | Create new → copy → rename |

## Performance Patterns

| Pattern | When | Impact |
|---------|------|--------|
| Covering index | Frequent queries with few columns | Index-only scan |
| `EXPLAIN ANALYZE` (8.0.18+) | Query optimization | Actual vs estimated rows |
| Buffer pool tuning | All deployments | `innodb_buffer_pool_size = 70-80% RAM` |
| Connection pooling (ProxySQL) | High concurrency | Fewer actual connections |
| `INSERT ... ON DUPLICATE KEY UPDATE` | Upsert operations | Single roundtrip |
| Prepared statements | Repeated queries | Parse once, execute many |

## Security Checklist

- [ ] No root user from application
- [ ] SSL/TLS on connections (`REQUIRE SSL`)
- [ ] Parameterized queries only (no interpolation)
- [ ] `sql_mode` includes `STRICT_TRANS_TABLES`
- [ ] User privileges follow least privilege principle
- [ ] Binary log enabled for point-in-time recovery
- [ ] `general_log` disabled in production (performance + security)

## Audit Commands

```bash
# Find wrong charset
rg "utf8[^m]|latin1|ascii" --type sql

# Find SELECT * usage
rg "SELECT \*" --type sql --type py

# Find LIKE with leading wildcard
rg "LIKE '%|LIKE \"%|LIKE concat\('%'" --type sql --type py

# Find ORDER BY RAND
rg "ORDER BY RAND\(\)" --type sql --type py

# Find raw SQL (potential injection)
rg "execute\(\"" --type py | rg -v "execute\(\"%s"

# Find missing online DDL hints
rg "ALTER TABLE" --type sql | rg -v "ALGORITHM|INPLACE|pt-online"
```
