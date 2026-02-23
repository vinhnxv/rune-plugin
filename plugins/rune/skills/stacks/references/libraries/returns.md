# Returns Library Patterns for Rune

## Quick Reference

| Scenario | Pattern | Severity if violated |
|----------|---------|---------------------|
| Bare `.unwrap()` on Result | Use `.value_or()` or pattern match | P1 |
| Mixing Result with try/except | Choose one error handling strategy | P2 |
| Missing `@safe` on IO functions | Wrap exceptions at boundary | P2 |
| `Success(None)` for missing data | Use `Maybe`/`Some`/`Nothing` | P3 |
| Unused Failure value | Log or propagate the error | P2 |
| `.bind()` chain without error handler | Add `.lash()` or `.alt()` | P2 |

## Key Rules

### Rule 1: Result/Success/Failure
- BAD: `try: result = do_thing() except: return None`
- GOOD: `Result[SuccessType, FailureType]` with explicit type parameters
- Detection: `rg "Result\[|Success\(|Failure\(" --type py`

### Rule 2: @safe Decorator
- BAD: Manual try/except wrapping in every function
- GOOD: `@safe` decorator to auto-wrap exceptions into `Failure`
- Detection: `rg "@safe\b" --type py` (check IO boundary functions)

### Rule 3: Pipeline Composition with .bind()
- BAD: Nested if/else for each step
- GOOD: `result.bind(step1).bind(step2).bind(step3)`
- Detection: `rg "\.bind\(|\.map\(|\.lash\(" --type py`

### Rule 4: Maybe/Some/Nothing
- BAD: `Result[User, str]` where failure is "not found" (not an error)
- GOOD: `Maybe[User]` for optional values (Some/Nothing)
- Detection: `rg "Maybe\[|Some\(|Nothing" --type py`

### Rule 5: FastAPI Integration
- BAD: `return result.unwrap()` in route handler (crashes on Failure)
- GOOD: Pattern match Result → return HTTP response with appropriate status
```python
match service_result:
    case Success(data):
        return JSONResponse(data, status_code=200)
    case Failure(NotFoundError()):
        raise HTTPException(status_code=404)
    case Failure(ValidationError() as e):
        raise HTTPException(status_code=422, detail=str(e))
```
- Detection: `rg "\.unwrap\(\)" --type py` in route/controller files

## Anti-Patterns

| Anti-Pattern | Why It's Bad | Fix |
|-------------|-------------|-----|
| `.unwrap()` in production | Crashes on Failure | `.value_or(default)` or pattern match |
| Mixing `Result` + `try/except` | Two error handling strategies | Pick one per layer |
| `Failure("")` (empty string) | No error context | Typed error class: `Failure(NotFoundError(...))` |
| Ignoring `.lash()` | Failure silently propagated | Add error handling at chain end |
| `Result[Any, Any]` | No type safety | Specific success/failure types |

## Patterns

### Layer Boundaries
```
API Layer:      try/except → Result (convert at boundary)
Service Layer:  Result[T, DomainError] (pure functional)
Repository:     @safe decorator (wrap IO exceptions)
```

### Error Type Hierarchy
```python
class DomainError(Exception): ...
class NotFoundError(DomainError): ...
class ValidationError(DomainError): ...
class PermissionError(DomainError): ...
```

## Audit Commands

```bash
# Find bare unwrap
rg "\.unwrap\(\)" --type py

# Find mixed error handling
rg "try:|except:" --type py -l | xargs rg "Result\[|@safe"

# Find untyped Results
rg "Result\[Any" --type py

# Find Failure without error type
rg 'Failure\("' --type py

# Find @safe usage
rg "@safe\b" --type py
```
