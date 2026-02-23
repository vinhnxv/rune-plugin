# FastAPI Patterns for Rune

## Quick Reference

| Scenario | Pattern | Severity if violated |
|----------|---------|---------------------|
| Route without response_model | Add `response_model=Schema` | P2 |
| Direct DB access in route handler | Use dependency injection (`Depends()`) | P2 |
| Missing input validation | Use Pydantic model for request body | P1 |
| IDOR vulnerability | Verify resource ownership in handler | P1 |
| Sync function in async route | Use `async def` or `run_in_executor` | P2 |
| Missing error handler | Add `@app.exception_handler` | P2 |

## Key Rules

### Rule 1: Route Design (FA-001)
- BAD: `@app.get("/user/{id}")` returning raw dict
- GOOD: `@app.get("/user/{id}", response_model=UserResponse, status_code=200)`
- Detection: `rg "@app\.(get|post|put|delete|patch)\(" --type py`

### Rule 2: Pydantic Validation (FA-002)
- BAD: `request.json()` with manual validation
- GOOD: Type-annotated parameter with Pydantic model
- Detection: `rg "request\.json\(\)|request\.body\(\)" --type py`

### Rule 3: Dependency Injection (FA-003)
- BAD: Global database session or service instantiation in handler
- GOOD: `async def handler(db: AsyncSession = Depends(get_db)):`
- Detection: `rg "Session\(\)|engine\.connect\(\)" --type py` in route files

### Rule 4: IDOR Prevention (FA-004)
- BAD: `@app.get("/users/{user_id}/orders")` without ownership check
- GOOD: Verify `current_user.id == user_id` or use scoped query
- Detection: `rg "Path\(|{.*_id}" --type py` in router files

### Rule 5: Error Responses (FA-005)
- BAD: Unhandled exceptions returning 500 with stack trace
- GOOD: Custom `HTTPException` with consistent error schema
- Detection: `rg "raise HTTPException" --type py` (check for consistency)

## Anti-Patterns

| Anti-Pattern | Why It's Bad | Fix |
|-------------|-------------|-----|
| `@app.on_event("startup")` | Deprecated in newer FastAPI | Use `lifespan` context manager |
| Sync `def` route handlers | Blocks event loop | Use `async def` |
| `response.dict()` | Deprecated Pydantic v2 | Use `response.model_dump()` |
| Background tasks for long work | Not reliable | Use Celery/ARQ/task queue |
| Mutable default in Depends | Shared state across requests | Factory function |

## Performance Patterns

| Pattern | When | Impact |
|---------|------|--------|
| `response_model_exclude_unset` | Partial responses | Smaller payloads |
| Async DB sessions | All DB operations | Non-blocking I/O |
| `ORJSONResponse` | High-throughput JSON APIs | 2-3x faster serialization |
| Streaming responses | Large file downloads | Constant memory |
| Connection pooling | Production deployment | Fewer DB connections |

## Security Checklist

- [ ] All routes have authentication middleware
- [ ] CORS configured with specific origins (not `*`)
- [ ] Rate limiting on auth endpoints
- [ ] Input validation via Pydantic (not manual)
- [ ] IDOR checks on all resource-scoped endpoints
- [ ] No sensitive data in error responses
- [ ] OpenAPI schema matches actual behavior

## Audit Commands

```bash
# Find routes without response_model
rg "@(app|router)\.(get|post|put|delete|patch)\([^)]*\)" --type py | rg -v "response_model"

# Find direct DB session creation
rg "Session\(\)|create_engine\(" --type py

# Find IDOR risks (path params with _id)
rg "@(app|router)\.(get|post|put|delete|patch).*\{.*_id\}" --type py

# Find missing async
rg "def (get_|create_|update_|delete_)" --type py | rg -v "async"

# Find deprecated patterns
rg "on_event|\.dict\(\)" --type py
```
