# DDD Patterns for Rune

## Quick Reference

| Scenario | Pattern | Severity if violated |
|----------|---------|---------------------|
| Anemic domain model (entity with only getters) | Add behavior methods to entity | P2 |
| Infrastructure import in domain layer | Reverse dependency direction | P1 |
| Missing aggregate boundary | Define aggregate root | P2 |
| Repository returns ORM model (not entity) | Map to domain entity | P2 |
| Domain event not raised | Raise event in entity method | P3 |
| Ubiquitous language mismatch | Align code names with domain terms | P2 |

## Layer Architecture

```
┌─────────────────────────────────┐
│          API Layer              │  Routes, controllers, serializers
│  (depends on Application)       │
├─────────────────────────────────┤
│       Application Layer         │  Use cases, services, DTOs
│  (depends on Domain)            │
├─────────────────────────────────┤
│         Domain Layer            │  Entities, value objects, events
│  (depends on NOTHING)           │  ← Pure business logic
├─────────────────────────────────┤
│     Infrastructure Layer        │  Repos, adapters, external services
│  (implements Domain interfaces) │
└─────────────────────────────────┘
```

**Import rule**: Domain NEVER imports from Infrastructure, Application, or API. Infrastructure implements Domain interfaces.

## Key Rules

### Rule 1: Entity Design
- BAD: Data class with public attributes and no methods
- GOOD: Entity with identity, behavior methods, and invariant enforcement
```python
class Order:
    def __init__(self, id: OrderId, items: list[OrderItem]):
        self._id = id
        self._items = items
        self._status = OrderStatus.DRAFT

    def add_item(self, item: OrderItem) -> None:
        if self._status != OrderStatus.DRAFT:
            raise DomainError("Cannot add items to non-draft order")
        self._items.append(item)
```
- Detection: `rg "class \w+(Entity|Aggregate)" --type py` then check for behavior methods

### Rule 2: Value Objects
- BAD: `email: str` (no validation, mutable)
- GOOD: `email: Email` (validated, immutable, equality by value)
```python
@dataclass(frozen=True)
class Email:
    value: str
    def __post_init__(self):
        if not re.match(r'^[\w.-]+@[\w.-]+\.\w+$', self.value):
            raise ValueError(f"Invalid email: {self.value}")
```
- Detection: `rg "frozen=True|@dataclass" --type py` in domain directories

### Rule 3: Aggregate Boundaries
- BAD: Service modifies child entities directly (bypassing aggregate root)
- GOOD: All modifications go through aggregate root
- Detection: Review `domain/` for entities that should be aggregates

### Rule 4: Repository Pattern
- BAD: `session.query(UserModel).filter_by(id=id).first()`
- GOOD: `repo.get(user_id) -> User` (returns domain entity, not ORM model)
- Detection: `rg "class \w+Repository" --type py` (check return types)

### Rule 5: Domain Events
- BAD: Service sends email directly after user creation
- GOOD: Entity raises `UserCreated` event → handler sends email
```python
class User:
    def register(self, email: Email, password: HashedPassword):
        self._events.append(UserCreated(user_id=self.id, email=email))
```
- Detection: `rg "Event\(|_events|raise_event|domain_events" --type py`

### Rule 6: Ubiquitous Language
- BAD: Code uses `customer` but domain experts say `client`
- GOOD: Code terms match domain glossary exactly
- Detection: Compare code identifiers with domain documentation

## Anti-Patterns

| Anti-Pattern | Why It's Bad | Fix |
|-------------|-------------|-----|
| Anemic domain model | Business logic scattered in services | Move behavior to entities |
| Infrastructure in domain | Couples domain to technical details | Depend on protocols/interfaces |
| God aggregate | Too many entities in one aggregate | Split by consistency boundary |
| Primitive obsession | Strings for domain concepts | Value objects (Email, Money, etc.) |
| Missing bounded context | Domain concepts blur across modules | Define explicit boundaries |
| CRUD service | No domain logic encapsulation | Use case / command handler |

## Directory Structure

```
src/
├── domain/           # Pure domain (NO external imports)
│   ├── entities/
│   ├── value_objects/
│   ├── events/
│   ├── exceptions/
│   └── protocols/    # Repository interfaces
├── application/      # Use cases, DTOs
│   ├── services/
│   ├── commands/
│   └── queries/
├── infrastructure/   # Implementations
│   ├── repositories/
│   ├── adapters/
│   └── persistence/
└── api/              # Routes, controllers
    ├── routes/
    └── schemas/
```

## Audit Commands

```bash
# Find domain layer importing infrastructure
rg "from.*infrastructure|import.*infrastructure" domain/ --type py

# Find anemic entities (classes without methods)
rg "class \w+.*:" domain/entities/ --type py -A 20 | rg "def " | rg -v "__init__|__repr__|__eq__"

# Find repositories returning ORM models
rg "-> \w+Model" --type py

# Find domain events
rg "Event\(|DomainEvent|@event" --type py

# Find value objects
rg "frozen=True" domain/ --type py

# Find ubiquitous language violations (example)
rg "customer|client" domain/ --type py
```
