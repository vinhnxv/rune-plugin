# Dependency Injection Patterns for Rune

## Quick Reference

| Scenario | Pattern | Severity if violated |
|----------|---------|---------------------|
| Service Locator pattern | Use constructor injection | P1 |
| Global state / singleton abuse | Use DI container scoping | P2 |
| Circular dependency | Restructure with interfaces | P1 |
| Missing protocol/interface binding | Bind abstract → concrete | P2 |
| Container injected as dependency | Inject specific services | P2 |
| Missing cleanup on scoped services | Use context managers or dispose | P1 |

## DI Frameworks by Language

| Language | Framework | Scope Model |
|----------|-----------|-------------|
| Python | Dishka | APP → REQUEST → ACTION |
| Python | dependency-injector | Singleton, Factory, Resource |
| TypeScript | tsyringe | Singleton, Transient |
| TypeScript | inversify | Singleton, Request, Transient |
| PHP | PHP-DI | Singleton, Factory |
| PHP | Laravel Container | Singleton, Bind, Instance |
| Rust | (manual DI) | Ownership-based lifetime |

## Key Rules

### Rule 1: Constructor Injection
- BAD: `service.set_repository(repo)` (setter injection)
- BAD: `repo = Container.get(Repository)` (service locator)
- GOOD: `def __init__(self, repo: Repository): self._repo = repo`
- Detection: `rg "Container\.get\(|container\.resolve\(" --type py --type ts`

### Rule 2: Scope Management
- **Singleton** (APP scope): Stateless services, configuration, caches
- **Request** (REQUEST scope): Database sessions, user context, request-specific state
- **Transient** (ACTION scope): Short-lived, per-use, no shared state
- Detection: `rg "scope=|singleton|transient|Scope\." --type py --type ts`

### Rule 3: Protocol/Interface Binding
- BAD: Depending on `PostgresUserRepository` directly
- GOOD: Depending on `UserRepository` (Protocol/Interface), bound in container
```python
# Python (Dishka)
@provide(scope=Scope.REQUEST)
def get_repo(self, session: AsyncSession) -> UserRepository:
    return PostgresUserRepository(session)

# TypeScript (tsyringe)
container.register<UserRepository>("UserRepository", {
    useClass: PostgresUserRepository
});
```
- Detection: `rg "Protocol\)|Interface\b" --type py --type ts`

### Rule 4: Circular Dependency Detection
- Symptom: `ImportError` or `Cannot resolve circular dependency`
- Fix: Extract shared interface, use lazy injection, or restructure
- Detection: `rg "from.*import|import.*from" --type py` — build dependency graph

### Rule 5: Testing with DI
- BAD: Mocking internal details, patching global state
- GOOD: Override container bindings with test implementations
```python
# Dishka
async with make_async_container(
    ProductionProvider(),
    overrides=[TestProvider()]
) as container:
    service = await container.get(UserService)
```
- Detection: `rg "override|mock_container|TestProvider" --type py`

## Anti-Patterns

| Anti-Pattern | Why It's Bad | Fix |
|-------------|-------------|-----|
| Service Locator | Hidden dependencies, untestable | Constructor injection |
| Container as dependency | God object pattern | Inject specific services |
| Global state | Race conditions, hard to test | Scoped injection |
| Over-injection (>5 deps) | Class doing too much | Split into smaller services |
| Concrete class injection | Tight coupling | Protocol/Interface binding |
| Missing dispose/cleanup | Resource leaks | Scope lifecycle management |

## Scope Leak Detection

A scope leak occurs when a short-lived dependency is injected into a longer-lived service:

```
DANGER: APP-scoped service depends on REQUEST-scoped database session
        → Session outlives request → stale data, connection leak

FIX: Either narrow the service scope or inject a factory
```

| Parent Scope | Can Depend On | Cannot Depend On |
|-------------|--------------|-----------------|
| APP (singleton) | APP only | REQUEST, ACTION |
| REQUEST | APP + REQUEST | ACTION |
| ACTION | APP + REQUEST + ACTION | (none) |

## Audit Commands

```bash
# Find service locator patterns
rg "Container\.get\(|container\.resolve\(|locator\." --type py --type ts --type php

# Find direct instantiation (bypassing DI)
rg "= new \w+Service\(|= \w+Service\(" --type py --type ts | rg -v "test|mock|Test|Mock"

# Find scope declarations
rg "Scope\.|singleton|transient|scoped" --type py --type ts

# Find circular dependency risks (imports)
rg "from.*import" domain/ --type py | sort | uniq -d

# Find classes with too many dependencies (>5 params)
rg "def __init__\(self," --type py -A 1

# Find missing protocol bindings
rg "Protocol\):" --type py -l
```
