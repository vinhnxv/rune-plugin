# Pydantic Patterns for Rune

## Quick Reference

| Scenario | Pattern | Severity if violated |
|----------|---------|---------------------|
| `Any` type in model field | Use specific type or `Unknown` | P2 |
| Missing `model_config` strict mode | Add `ConfigDict(strict=True)` where needed | P3 |
| Circular model references | Use `TYPE_CHECKING` + `model_rebuild()` | P2 |
| `@validator` (Pydantic v1) | Migrate to `@field_validator` (v2) | P2 |
| Overly permissive validator | Validate specific constraints | P2 |
| Schema mismatch with API docs | Align response_model with OpenAPI | P1 |

## Key Rules

### Rule 1: Model Inheritance and Composition
- BAD: Duplicating fields across models
- GOOD: Base model with shared fields, `model_config` for customization
- Detection: `rg "class \w+\(BaseModel\)" --type py` (review for field duplication)

### Rule 2: field_validator vs model_validator
- BAD: Using `model_validator` for single-field checks
- GOOD: `@field_validator('email')` for single-field, `@model_validator(mode='after')` for cross-field
- Detection: `rg "@(field_validator|model_validator)" --type py`

### Rule 3: Strict Mode Decision
- **Use strict mode** (`ConfigDict(strict=True)`): API input validation, security-sensitive models
- **Use lax mode** (default): Internal data transformation, config loading, database ORM mapping
- Detection: `rg "ConfigDict|model_config" --type py`

### Rule 4: JSON Schema Alignment
- BAD: Schema generated from model diverges from API documentation
- GOOD: `model.model_json_schema()` matches OpenAPI spec exactly
- Detection: Compare `model_json_schema()` output against API docs

### Rule 5: Computed Fields
- BAD: Property that should be serialized but isn't
- GOOD: `@computed_field` decorator for derived values in serialization
- Detection: `rg "@computed_field|@property" --type py` in model files

## Anti-Patterns

| Anti-Pattern | Why It's Bad | Fix |
|-------------|-------------|-----|
| `Any` as field type | Bypasses validation | Specific type or `object` |
| `.dict()` (v1 API) | Deprecated in Pydantic v2 | Use `.model_dump()` |
| `from_orm()` (v1 API) | Deprecated | Use `model_validate()` |
| Mutable default in field | Shared state between instances | `Field(default_factory=list)` |
| Nested `dict` instead of model | No validation on nested data | Nested Pydantic model |
| `validate_default=False` | Defaults bypass validation | Set `True` for safety |

## Performance Patterns

| Pattern | When | Impact |
|---------|------|--------|
| `model_validate()` | ORM → Pydantic | ~2x faster than manual dict conversion |
| `TypeAdapter` | Validating non-model types | Avoids full model overhead |
| `model_dump(exclude_unset=True)` | PATCH endpoints | Smaller payloads |
| `model_dump(mode='python')` | Internal processing | Skips JSON serialization step |
| Frozen models | Immutable value objects | Hashable, cache-friendly |

## Audit Commands

```bash
# Find Pydantic v1 patterns
rg "\.dict\(\)|\.json\(\)|from_orm|@validator\b" --type py

# Find Any type usage
rg ": Any\b" --type py | rg -v "typing.Any"

# Find models without strict mode
rg "class \w+\(BaseModel\)" --type py -l

# Find mutable defaults
rg "Field\(default=\[|Field\(default=\{" --type py

# Find nested dict instead of model
rg ": dict\[|: Dict\[" --type py
```
