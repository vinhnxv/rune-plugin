# Service Startup Protocol

## Auto-Detection Strategy (v1)

```
Detection order (first match wins):

1. docker-compose.yml / compose.yml exists
   → T3 path traversal guard: canonicalize path before use
     composePath = Bash(`realpath --relative-base="$(pwd)" docker-compose.yml 2>/dev/null || realpath --relative-base="$(pwd)" compose.yml 2>/dev/null`)
     if composePath starts with "/" or contains ".." → reject with error ("Docker Compose path traversal detected")
   → docker compose up -d --wait
   → Hard timeout: 3 minutes

2. talisman.testing.service.startup_command is set
   → Validate: must match SAFE_TEST_COMMAND_PATTERN (/^[a-zA-Z0-9._\-\/ ]+$/)
   → Reject with error if validation fails (command injection prevention)
   → Run the validated command with quoted variable: Bash(`"${startup_command}"`)
   → Example: "bin/dev", "npm run dev"

3. package.json scripts contains "dev" or "start"
   → npm run dev (background) OR npm start (background)

4. Makefile contains "serve" or "dev" target
   → make dev (background)

5. Nothing found
   → WARN: "No service startup detected. Services may already be running."
   → Skip STEP 3 entirely — proceed to tests
```

## Health Check Protocol

```
After service startup, verify readiness:

1. Determine health endpoint:
   - /health, /healthz, /api/health (try in order)
   - Or: talisman.testing.tiers.e2e.base_url + /health

2. Poll loop:
   - HTTP GET to health endpoint
   - Interval: 2 seconds
   - Max attempts: 30 (= 60s total)
   - Success: any HTTP 2xx response
   - Timeout: skip integration/E2E tiers, unit still runs

3. On timeout:
   - Capture diagnostic: docker compose logs (last 50 lines)
   - Write to test report as WARN
   - Unit tests still execute (they don't need services)
```

## Docker-Specific Patterns

### Startup
```bash
# Preferred (Docker Compose v2 with --wait)
docker compose up -d --wait

# Fallback (older Docker)
docker compose up -d
# Then poll health checks manually
```

### Health Checks in docker-compose.yml
```yaml
services:
  postgres:
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-postgres}"]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 10s

  redis:
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 3s
      timeout: 2s
      retries: 5

  app:
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
```

### Container ID Recording
```bash
# Record for crash recovery
docker compose ps --format json > tmp/arc/{id}/docker-containers.json
```

### Cleanup
```bash
# Normal cleanup
docker compose down --timeout 10 --remove-orphans

# Fallback: kill by container IDs
docker kill $(jq -r '.[].ID' tmp/arc/{id}/docker-containers.json) 2>/dev/null

# Nuclear: remove volumes too
docker compose down -v --timeout 10 --remove-orphans
```

## Startup Timeout Budgets

| Service | Typical cold start | Recommended timeout |
|---------|--------------------|---------------------|
| PostgreSQL | 3-8s | 30s |
| Redis | 1-3s | 15s |
| Node.js app | 5-15s | 60s |
| Full stack (compose up) | 15-40s | 120s |

## Port Detection

```bash
# From docker-compose.yml
docker compose config --format json | jq '.services[].ports[]'

# From talisman
# talisman.testing.tiers.e2e.base_url → extract port

# From package.json (heuristic)
grep -o 'PORT=[0-9]*' package.json || echo "3000"
```

## Graceful Degradation

If service startup fails at any point:
1. Log the failure diagnostic to test report
2. Skip integration and E2E tiers
3. Unit tests still run (they use mocks, no service dependency)
4. Phase 7.7 still produces a useful report (partial coverage)
