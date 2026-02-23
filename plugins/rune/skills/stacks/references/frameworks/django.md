# Django Patterns for Rune

## Quick Reference

| Scenario | Pattern | Severity if violated |
|----------|---------|---------------------|
| Missing `select_related`/`prefetch_related` | Add to QuerySet | P2 |
| CSRF exemption without justification | Remove `@csrf_exempt` or document reason | P1 |
| Raw SQL without parameterization | Use ORM or `params=[]` | P1 |
| Admin model without `readonly_fields` | Restrict sensitive fields | P2 |
| Signal with side effects | Use explicit service calls | P2 |
| Migration with `RunSQL` lock risk | Use `AddField(null=True)` + backfill | P1 |

## Key Rules

### Rule 1: Query Optimization
- BAD: `for order in user.orders.all(): print(order.product.name)` (N+1)
- GOOD: `user.orders.select_related('product').all()`
- Detection: `rg "\.all\(\)|\.filter\(" --type py` in view/serializer files

### Rule 2: CSRF Protection
- BAD: `@csrf_exempt` on state-changing endpoints
- GOOD: Include CSRF token in all forms/AJAX
- Detection: `rg "csrf_exempt" --type py`

### Rule 3: Admin Security
- BAD: `class UserAdmin(admin.ModelAdmin): pass`
- GOOD: Explicit `list_display`, `readonly_fields`, `list_filter`
- Detection: `rg "class \w+Admin.*ModelAdmin" --type py`

### Rule 4: Signal Anti-Patterns
- BAD: `post_save` signal that sends emails or modifies other models
- GOOD: Explicit service call in view/serializer
- Detection: `rg "post_save|pre_save|post_delete" --type py`

### Rule 5: Migration Safety
- BAD: `AddField` with `default=value` on large table (locks table)
- GOOD: `AddField(null=True)` → backfill → `AlterField(null=False)`
- Detection: Review migration files for lock-prone operations

## Anti-Patterns

| Anti-Pattern | Why It's Bad | Fix |
|-------------|-------------|-----|
| `objects.all()` in templates | Unbounded queries | Paginate or limit |
| Fat models | God class, hard to test | Service layer |
| `settings.py` secrets | Committed to VCS | `django-environ` or env vars |
| `ForeignKey(on_delete=CASCADE)` default | Accidental data deletion | Choose `PROTECT` or `SET_NULL` |
| Global middleware for auth | Applies everywhere unnecessarily | Per-view/per-route decorators |

## Performance Patterns

| Pattern | When | Impact |
|---------|------|--------|
| `select_related()` | ForeignKey access | Eliminates N+1 (JOIN) |
| `prefetch_related()` | ManyToMany/reverse FK | Eliminates N+1 (2 queries) |
| `only()` / `defer()` | Large models, partial field access | Less data transfer |
| `iterator()` | Processing large QuerySets | Constant memory |
| Database indexes | Filtered/sorted fields | Query speed |
| `cached_property` | Expensive computed properties | Single computation per instance |

## Security Checklist

- [ ] CSRF middleware enabled (not disabled globally)
- [ ] `ALLOWED_HOSTS` configured (not `['*']`)
- [ ] `DEBUG = False` in production
- [ ] `SECRET_KEY` not hardcoded
- [ ] Clickjacking middleware enabled (`X-Frame-Options`)
- [ ] SQL injection: no raw SQL with string formatting
- [ ] XSS: auto-escaping not disabled in templates
- [ ] Admin: custom admin site with restricted access

## Audit Commands

```bash
# Find N+1 risks
rg "\.all\(\)|\.filter\(" --type py -l

# Find CSRF exemptions
rg "csrf_exempt" --type py

# Find raw SQL
rg "\.raw\(|\.extra\(|RawSQL\(|cursor\(\)" --type py

# Find admin without restrictions
rg "class \w+Admin.*ModelAdmin" --type py

# Find signal usage
rg "(post_save|pre_save|post_delete|pre_delete)\.connect\b|@receiver\(" --type py

# Find migration risks
rg "RunSQL|AlterField|RemoveField" plugins/*/migrations/ --type py
```
