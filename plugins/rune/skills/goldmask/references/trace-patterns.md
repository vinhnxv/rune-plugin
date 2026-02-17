# Trace Patterns — Grep/Glob per Language per Layer

Patterns for Impact Layer tracers to find dependencies across 5 layers. Each tracer uses these to IDENTIFY symbols and TRACE usages.

## Data Layer Tracer

| Language | Pattern Type | Grep Pattern | Glob |
|----------|-------------|-------------|------|
| Python | ORM models | `class \w+\(.*Model\)` | `**/models.py`, `**/models/*.py` |
| Python | Migrations | `class Migration` | `**/migrations/*.py` |
| Python | Serializers | `class \w+Serializer` | `**/serializers.py` |
| TypeScript | Prisma schema | `model \w+ \{` | `**/schema.prisma` |
| TypeScript | TypeORM entity | `@Entity\(\)` | `**/*.entity.ts` |
| Ruby | ActiveRecord | `class \w+ < ApplicationRecord` | `app/models/*.rb` |
| Go | GORM model | `type \w+ struct` + `gorm:` tag | `**/model*.go` |
| Rust | Diesel schema | `table!` | `**/schema.rs` |

## API Contract Tracer

| Language | Pattern Type | Grep Pattern | Glob |
|----------|-------------|-------------|------|
| Python | FastAPI routes | `@(app\|router)\.(get\|post\|put\|delete\|patch)` | `**/routes*.py`, `**/api/*.py` |
| Python | Django URLs | `path\(` | `**/urls.py` |
| TypeScript | Express routes | `router\.(get\|post\|put\|delete\|patch)` | `**/routes/*.ts`, `**/*.controller.ts` |
| TypeScript | Next.js API | `export (async )?function (GET\|POST\|PUT\|DELETE)` | `**/api/**/route.ts` |
| Ruby | Rails routes | `(get\|post\|put\|delete\|resources)` | `config/routes.rb` |
| Go | net/http | `(HandleFunc\|Handle)\(` | `**/*handler*.go`, `**/*router*.go` |
| Rust | Actix/Axum | `#\[(get\|post)\(` or `.route\(` | `**/routes*.rs` |

## Business Logic Tracer

| Language | Pattern Type | Grep Pattern | Glob |
|----------|-------------|-------------|------|
| Python | Service classes | `class \w+Service` | `**/services/*.py`, `**/service.py` |
| Python | Domain models | `class \w+\(BaseModel\)` | `**/domain/*.py` |
| TypeScript | Service classes | `class \w+Service` | `**/services/*.ts`, `**/*.service.ts` |
| TypeScript | Validators | `(validate\|check\|assert)\w+` | `**/validators/*.ts` |
| Ruby | Service objects | `class \w+Service` | `app/services/*.rb` |
| Go | Business logic | `func.*Service\)` (method on Service struct) | `**/service*.go` |
| Rust | Domain types | `pub struct \w+` + `impl \w+` | `**/domain/*.rs` |

## Event/Message Tracer

| Language | Pattern Type | Grep Pattern | Glob |
|----------|-------------|-------------|------|
| Python | Event publish | `(emit\|publish\|dispatch)\(` | `**/events/*.py` |
| Python | Event subscribe | `@(on\|subscribe\|handler)` | `**/handlers/*.py`, `**/consumers/*.py` |
| TypeScript | EventEmitter | `(emit\|on\|addEventListener)\(` | `**/events/*.ts` |
| TypeScript | Message queue | `(publish\|subscribe\|send)\(` | `**/queue/*.ts`, `**/messaging/*.ts` |
| Ruby | ActiveJob | `class \w+ < ApplicationJob` | `app/jobs/*.rb` |
| Go | Channel/NATS | `(Publish\|Subscribe)\(` | `**/event*.go`, `**/messaging*.go` |
| Rust | Tokio channels | `(send\|recv)\(` | `**/events/*.rs` |

## Config/Dependency Tracer

| Language | Pattern Type | Grep Pattern | Glob |
|----------|-------------|-------------|------|
| All | Env reads | `(os\.environ\|process\.env\|ENV\[)` | `.env*`, `**/config.*` |
| All | Docker | `FROM\|EXPOSE\|ENV` | `Dockerfile*`, `docker-compose*.yml` |
| All | CI/CD | `(run:\|script:\|steps:)` | `.github/workflows/*.yml`, `.gitlab-ci.yml` |
| Python | Requirements | package name | `requirements*.txt`, `pyproject.toml` |
| TypeScript | Package deps | package name | `package.json` |
| Ruby | Gemfile | `gem '` | `Gemfile` |
| Go | Go modules | module path | `go.mod`, `go.sum` |
| Rust | Cargo deps | crate name | `Cargo.toml` |

## Usage Notes

- Tracers should grep for **symbol definitions** in changed files first, then grep for **usages** of those symbols across the codebase.
- Always include test files in traces — `**/*test*`, `**/*spec*`.
- Glob patterns use `**` for recursive directory matching.
- Adjust patterns for project conventions discovered during SCOPE step.
