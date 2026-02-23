# API Discovery — Tier 3 Endpoint Contract Detection

> Discovers API endpoints by scanning route definitions across multiple web frameworks.

## Overview

APIs are discovered by scanning for route/endpoint definitions using framework-specific patterns. Each endpoint traces the full request/response lifecycle.

## Detection Patterns

| Framework | Pattern | Example |
|-----------|---------|---------|
| Express/Koa | `app.get(`, `router.post(` | `router.post('/api/users', handler)` |
| FastAPI | `@app.get(`, `@router.post(` | `@router.post("/users")` |
| Spring | `@GetMapping(`, `@PostMapping(` | `@PostMapping("/api/users")` |
| Go net/http | `http.HandleFunc(` | `http.HandleFunc("/users", handler)` |
| Rails | `resources :`, `get '`, `post '` | `resources :users` |
| Django | `path(`, `url(` | `path('api/users/', views.UserView)` |
| Flask | `@app.route(` | `@app.route('/users', methods=['POST'])` |
| Gin (Go) | `router.GET(`, `router.POST(` | `router.POST("/users", handler)` |
| Generic | `@Route(`, `@Api(` | Framework decorators |

## Endpoint Type Classification

Endpoints with unique risk profiles get security boosts:

| Type | Detection Pattern | Security Boost |
|------|-------------------|----------------|
| GraphQL | `/graphql`, `ApolloServer`, `graphene` | +3 |
| WebSocket | `ws://`, `wss://`, `socket.io`, `@WebSocket` | +3 |
| File Upload | `multer`, `formidable`, `FileUpload`, `multipart` | +2 |
| Redirect | `redirect_url`, `next=`, `return_to` | +2 |
| SSE | `text/event-stream`, `EventSource` | +1 |
| Batch/Bulk | `/batch`, `/bulk`, accepts array body | +2 |
| Health/Debug | `/health`, `/debug`, `/metrics` | +1 (flag) |

## Lifecycle Tracing

For each discovered endpoint, trace the full request/response lifecycle:

```
Route definition
  → Middleware chain (auth, rate-limit, CORS)
  → Request validator
  → Handler function
  → Business logic (service layer)
  → Response serializer
  → Error handler
  → API documentation
  → Test file
```

## apis.json Schema

```json
{
  "schema_version": 1,
  "apis": {
    "POST /api/auth/login": {
      "method": "POST",
      "path": "/api/auth/login",
      "handler_file": "src/controllers/auth.controller.ts",
      "handler_function": "login",
      "validator_file": "src/validators/auth.validator.ts",
      "serializer_file": "src/serializers/auth.serializer.ts",
      "middleware": ["src/middleware/rate-limiter.ts"],
      "doc_file": "docs/api/auth.md",
      "test_file": "tests/api/auth.test.ts",
      "workflow_ref": "auth-login",
      "auth": {
        "scheme": "none|bearer|session|api-key",
        "required_roles": [],
        "rate_limited": true,
        "csrf_protected": false
      },
      "endpoint_type": "standard|graphql|websocket|upload|redirect|sse|batch|health",
      "contract_snapshot": null,
      "last_audited": "ISO8601 or null",
      "findings": { "contract": 0, "validation": 0, "security": 0 },
      "status": "audited|never_audited|stale"
    }
  },
  "stats": {
    "total_endpoints": 45,
    "audited_endpoints": 20,
    "coverage_pct": 44.4
  }
}
```

## API Priority Scoring

```
api_priority = (
    0.30 * staleness_score(api)           +
    0.25 * handler_change_score(api)      +
    0.20 * security_sensitivity(api)      +
    0.15 * contract_complexity(api)       +
    0.10 * usage_estimate(api)
)
```

**security_sensitivity** (multi-factor):
```
security_sensitivity(api) = max(
    base_sensitivity(method, auth_level),
    endpoint_type_boost(api),
    middleware_gap_penalty(api),
    data_classification_boost(api)
)
```

Base sensitivity by route patterns:
- Public + writes data (POST/PUT/DELETE) → 10
- Auth-required + financial data → 9
- Admin-only → 7
- Read-only public → 3
- Internal/health check → 1

## Contract Drift Detection

Between audit sessions:

1. **Snapshot capture**: On first audit, record request params, response shape, status codes
2. **Drift detection**: On subsequent audit, diff implementation against snapshot → `API-DRIFT`
3. **OpenAPI reconciliation**: If project has openapi.json/swagger.yaml:
   - Undocumented endpoints → `API-INVENTORY`
   - Stale documentation → `API-DOC`
   - Signature mismatch → `API-DRIFT`

**Breaking change classification**:
- Removed required response field → P1
- Added required request parameter → P1
- Changed status code semantics → P2
- Added optional field → P3

## Framework Detection

Auto-detect frameworks from project dependencies:

```bash
# package.json (Node.js)
grep -l '"express"\|"koa"\|"fastify"\|"hapi"' package.json

# requirements.txt (Python)
grep -l 'fastapi\|flask\|django' requirements.txt Pipfile pyproject.toml

# pom.xml / build.gradle (Java/Spring)
grep -l 'spring-boot\|spring-web' pom.xml build.gradle

# go.mod (Go)
grep -l 'gin-gonic\|net/http\|echo' go.mod

# Gemfile (Ruby/Rails)
grep -l 'rails\|sinatra' Gemfile
```

Override via talisman:
```yaml
audit:
  incremental:
    tiers:
      apis:
        frameworks: ["express", "fastapi"]
```
