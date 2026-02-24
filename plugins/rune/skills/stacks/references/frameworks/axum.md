# Axum Patterns for Rune

## Quick Reference

| ID | Pattern | Severity |
|----|---------|----------|
| AXUM-001 | N+1 query — SQLx query inside loop | P1 |
| AXUM-002 | Extractor ordering — body-consuming extractor not last | P1 |
| AXUM-003 | IDOR — resource access without owner check | P1 |
| AXUM-004 | Missing input validation on Path params | P2 |
| AXUM-005 | Transaction boundary mismatch — side effects before commit | P2 |
| AXUM-006 | Unhandled extractor rejection — plain-text errors in API | P2 |
| AXUM-007 | Extension used for app-wide state — use State instead | P2 |
| AXUM-008 | Middleware without HandleErrorLayer — fallible Tower layer | P2 |
| AXUM-009 | `from_fn` without state access — use `from_fn_with_state` | P3 |
| AXUM-010 | Missing graceful shutdown — `with_graceful_shutdown` | P3 |

## Extractor Ordering

Axum distinguishes two extractor traits:

- **`FromRequestParts`** (State, Path, Query, HeaderMap, Extension) — read-only; can appear in any position
- **`FromRequest`** (Json, String, Bytes, Multipart) — consumes the request body; **MUST be the last parameter**

Violating the ordering rule:

- Axum 0.7: silent runtime HTTP 400
- Axum 0.8+: compile error for `Router::new().route()` handlers

```bash
# Detect handlers with Json not in last position
rg 'async fn.*\(.*Json<' --type rust
```

Fix: Move `Json<T>`, `String`, `Bytes`, or `Multipart` to the last parameter position.

## Extractor Rejection Handling

Without a custom rejection type, Axum returns plain-text `400 Bad Request` for malformed request bodies — breaking JSON API clients expecting consistent error envelopes.

**BAD**: Handler takes `Json<T>` directly — Axum sends plain-text rejection
**GOOD**: Return `Result<Json<T>, AppError>` and implement `IntoResponse` for `AppError`

Alternatively, use `#[from_request(rejection(AppError))]` derive macro or wrap extractors in `Result<Json<T>, JsonRejection>`.

```bash
# Find handlers with bare Json<T> (not wrapped in Result)
rg 'async fn.*\(.*Json<' --type rust
```

## State vs Extension

| | `State<T>` | `Extension<T>` |
|-|-----------|----------------|
| API version | Axum 0.6+ | Axum 0.5 (legacy) |
| Missing check | Compile error | Runtime 500 |
| Middleware access | `from_fn_with_state` | Extension extraction |
| Thread-safe | Yes | Yes |

**Rule**: Use `State<T>` for app-wide shared state. Only use `Extension<T>` for request-scoped data injected by middleware.

```bash
# Find legacy Extension usage for app state
rg 'Extension<(?!Request)' --type rust
```

## Tower Middleware

Tower layers wrap services. Layer ordering is **bottom-to-top** for requests (the LAST `.layer()` call runs FIRST on incoming requests).

Recommended production layer sequence (via `ServiceBuilder`):

```
TraceLayer (outermost — logs all requests)
  → HandleErrorLayer (converts middleware Err to HTTP response)
  → TimeoutLayer
  → ConcurrencyLimitLayer (innermost — closest to handler)
```

**Critical**: `TimeoutLayer` and `RateLimitLayer` can return `Err`. Without `HandleErrorLayer`, these errors propagate as opaque 500s instead of proper HTTP responses (408 Timeout, 429 Too Many Requests).

```bash
# Find ServiceBuilder without HandleErrorLayer before fallible layers
rg 'ServiceBuilder::new\(\)' --type rust -A 20
```

Flag: `.layer(TimeoutLayer)` or `.layer(RateLimitLayer)` not preceded by `.layer(HandleErrorLayer)`.

## SQLx Transaction Patterns

SQLx `Transaction<Postgres>` implements `Deref<Target = PgConnection>` — pool queries and transaction queries use the same API.

**Side effect ordering rule**: External calls (email, HTTP, cache) MUST occur AFTER `tx.commit().await`. Reason: `commit()` can fail; side effects executed inside the transaction block may be retried on error.

```rust
// BAD — side effect inside transaction
let mut tx = pool.begin().await?;
sqlx::query!("INSERT INTO orders ...").execute(&mut *tx).await?;
send_email(&order).await?;  // Wrong — commit hasn't happened yet
tx.commit().await?;

// GOOD — side effect after commit
let mut tx = pool.begin().await?;
sqlx::query!("INSERT INTO orders ...").execute(&mut *tx).await?;
tx.commit().await?;
send_email(&order).await?;  // Correct — commit succeeded
```

Note: `Transaction<T>` dropped without `commit()` auto-rollbacks — no explicit `.rollback()` needed on `?`.

```bash
# Detect side effects before commit
rg 'tx\.commit\(\)' --type rust -B 10
```

## N+1 Prevention

N+1 occurs when a query fires inside a loop — one SQL round-trip per iteration instead of one batch query.

```rust
// BAD — N+1 query
for user_id in user_ids {
    let orders = sqlx::query_as!(Order, "SELECT * FROM orders WHERE user_id = $1", user_id)
        .fetch_all(&pool).await?;
}

// GOOD — batch query (PostgreSQL)
let orders = sqlx::query_as!(Order,
    "SELECT * FROM orders WHERE user_id = ANY($1)",
    &user_ids
).fetch_all(&pool).await?;

// GOOD — batch query (MySQL)
// Use a dynamic IN clause builder
```

```bash
# Detect queries inside loops (multiline)
rg -U 'for .+\{[^}]*\.fetch' --type rust --multiline

# Broader detection
rg 'sqlx::query' --type rust -A 3
```

## Security Checklist

- [ ] IDOR: All resource-scoped endpoints scope SQL WHERE to `user_id = $authenticated_user_id`
- [ ] Input validation: `Path<Uuid>` or `Path<i64>` instead of `Path<String>` where possible
- [ ] Timing-safe: Token/secret comparisons use `subtle::ConstantTimeEq` — not `==`
- [ ] Extractor rejections: Handlers return JSON error envelopes — not plain-text 400
- [ ] Transaction: Side effects (email, HTTP) occur AFTER `tx.commit()` — not inside
- [ ] State: `State<T>` used for app-wide config — not `Extension<T>` (silent 500 on missing)
- [ ] Middleware: `HandleErrorLayer` wraps all fallible Tower layers
- [ ] Graceful shutdown: `axum::serve().with_graceful_shutdown()` for containerized deployments

## Version Notes

### Axum 0.8+ Changes

| Feature | Axum 0.7 | Axum 0.8+ |
|---------|----------|-----------|
| Path parameter syntax | `:param` | `{param}` |
| Server initialization | `axum::Server` (hyper 0.14) | `axum::serve(TcpListener, router)` |
| Extractor ordering violation | Runtime HTTP 400 | Compile error |
| `from_fn` middleware | Available | Available + `from_fn_with_state` |

```bash
# Detect old-style path params (should be {param} in 0.8+)
rg '\.route\(".*:' --type rust

# Detect Axum version
rg '^\s*axum\s*=' Cargo.toml
rg '^\s*axum-extra\s*=' Cargo.toml
```

`axum-extra` in dependencies confirms Axum usage (extends extractor ecosystem).

## Audit Commands

```bash
# AXUM-001: N+1 query detection (multiline)
rg -U 'for .+\{[^}]*\.fetch' --type rust --multiline

# AXUM-002: Extractor ordering — Json not last
rg 'async fn.*\(.*Json<' --type rust

# AXUM-003: IDOR — missing owner check (review manually)
rg 'user_id|account_id' --type rust

# AXUM-004: Unvalidated Path<String>
rg 'Path<String>' --type rust

# AXUM-005: Transaction side effects before commit
rg 'tx\.commit\(\)' --type rust -B 10

# AXUM-006: Bare Json extraction without rejection handling
rg 'async fn.*\(.*Json<' --type rust

# AXUM-007: Legacy Extension for app state
rg 'Extension<(?!Request)' --type rust

# AXUM-008: Fallible middleware without HandleErrorLayer
rg 'ServiceBuilder::new\(\)' --type rust -A 20

# AXUM-009: from_fn without state access
rg 'from_fn\b' --type rust

# AXUM-010: Missing graceful shutdown (scope to src/, not tests/)
rg 'axum::serve\(' --type rust
```
