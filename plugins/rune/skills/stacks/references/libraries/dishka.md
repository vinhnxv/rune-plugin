# Dishka DI Patterns for Rune

## Quick Reference

| Scenario | Pattern | Severity if violated |
|----------|---------|---------------------|
| Missing scope on provider | Define explicit scope (APP/REQUEST/ACTION) | P2 |
| Scope leak (REQUEST-scoped in APP) | Fix scope hierarchy | P1 |
| Missing container cleanup | Use `async with` or `close()` | P1 |
| Direct instantiation (bypass DI) | Use `@provide` or `Depends()` | P2 |
| Over-scoping (APP for request-specific) | Narrow to REQUEST or ACTION scope | P2 |
| Missing protocol binding | Bind Protocol → Implementation | P3 |

## Scope Hierarchy

```
APP scope     → Singleton (created once, shared across all requests)
  └── REQUEST scope  → Per-request (created per HTTP request, scoped to request lifecycle)
       └── ACTION scope → Per-action (narrowest, created per use case invocation)
```

**Rule**: A provider in scope X can only depend on providers in scope X or broader.
- APP provider can depend on: APP providers only
- REQUEST provider can depend on: APP + REQUEST providers
- ACTION provider can depend on: APP + REQUEST + ACTION providers

## Key Rules

### Rule 1: Provider Patterns
- BAD: `container.get(MyService)` without `@provide`
- GOOD: `@provide(scope=Scope.REQUEST)` decorator on factory method
```python
class MyProvider(Provider):
    @provide(scope=Scope.REQUEST)
    async def get_service(self, repo: UserRepository) -> UserService:
        return UserService(repo)
```
- Detection: `rg "@provide|Provider\b" --type py`

### Rule 2: Protocol-Implementation Binding
- BAD: Depending on concrete class directly
- GOOD: Depend on Protocol, bind concrete in Provider
```python
class UserRepository(Protocol):
    async def get(self, id: int) -> User: ...

class PostgresUserRepository:
    async def get(self, id: int) -> User: ...

# In Provider:
@provide(scope=Scope.REQUEST)
def get_repo(self, session: AsyncSession) -> UserRepository:
    return PostgresUserRepository(session)
```
- Detection: `rg "Protocol\):" --type py` (check for corresponding `@provide`)

### Rule 3: Container Lifecycle
- BAD: `container = make_container(MyProvider())` without close
- GOOD: `async with make_async_container(MyProvider()) as container:`
- Detection: `rg "make_container|make_async_container" --type py` (check for context manager)

### Rule 4: FastAPI Integration
- BAD: Manual `Depends()` creating services inline
- GOOD: Dishka's `FromDishka[ServiceType]` or `inject` decorator
```python
@router.get("/users/{id}")
@inject
async def get_user(id: int, service: FromDishka[UserService]) -> UserResponse:
    return await service.get(id)
```
- Detection: `rg "FromDishka|@inject" --type py`

### Rule 5: Scope Leaks
- BAD: REQUEST-scoped database session injected into APP-scoped service
- GOOD: Match scopes — APP services only use APP dependencies
- Detection: Cross-reference `@provide(scope=...)` declarations

## Anti-Patterns

| Anti-Pattern | Why It's Bad | Fix |
|-------------|-------------|-----|
| Service Locator | Hidden dependencies, hard to test | Constructor injection via `@provide` |
| Global container | Shared mutable state | Scope-per-request pattern |
| Over-scoping (APP for DB session) | Connection leak, stale data | REQUEST or ACTION scope |
| Missing cleanup | Resource leak | `async with` or explicit `close()` |
| Circular dependency | Stack overflow at startup | Restructure with interfaces |
| Injecting container itself | God object, untestable | Inject specific dependencies |

## Testing Patterns

### Container Override
```python
async with make_async_container(
    MyProvider(),
    overrides=[mock_provider]  # Override specific bindings for test
) as container:
    service = await container.get(UserService)
```

### Mock Injection
```python
class MockProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_repo(self) -> UserRepository:
        return MockUserRepository()
```

## Audit Commands

```bash
# Find all providers
rg "@provide" --type py

# Find scope declarations
rg "scope=Scope\." --type py

# Find container creation (check for cleanup)
rg "make_container|make_async_container" --type py

# Find direct instantiation (bypass DI)
rg "= \w+Service\(|= \w+Repository\(" --type py | rg -v "@provide|mock|test|Mock"

# Find FromDishka usage
rg "FromDishka\[" --type py

# Find potential scope leaks
rg "Scope\.APP" --type py -l | xargs rg "AsyncSession|Connection"
```
