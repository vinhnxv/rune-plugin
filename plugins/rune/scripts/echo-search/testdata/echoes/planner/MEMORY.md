# Planner Echoes

## Inscribed — Plan: API Rate Limiting Strategy (2026-01-12)

**Source**: `rune:devise 20260112-rate-limiting`
**Confidence**: HIGH (full pipeline: brainstorm + 3 research agents + scroll review)

### Key Learnings

- **Token bucket vs sliding window**: Token bucket is simpler to implement but sliding window provides smoother rate limiting. Chose sliding window for user-facing API, token bucket for internal service-to-service calls.
- **Redis vs in-memory**: Redis required for distributed rate limiting across multiple API server instances. In-memory only works for single-instance deployments.
- **429 response headers matter**: Always include `Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers. Clients depend on these for backoff strategies.
- **Graduated penalties**: First violation gets soft limit (warning header), second gets 429, third gets temporary IP block. Progressive enforcement reduces false positives from legitimate burst traffic.

## Inscribed — Plan: Event-Driven Architecture Migration (2026-01-28)

**Source**: `rune:devise 20260128-event-driven`
**Confidence**: HIGH (full pipeline: brainstorm + 4 research agents + forge enrichment)

### Key Learnings

- **Start with domain events, not technical events**: `OrderPlaced` is better than `DatabaseRowInserted`. Domain events survive infrastructure changes; technical events create coupling.
- **Outbox pattern prevents dual-write failures**: Writing event to an outbox table in the same transaction as the business operation guarantees consistency. A separate poller publishes from outbox to the message broker.
- **Schema registry is mandatory for production**: Without a schema registry, producers can break consumers by changing event payloads. Use Avro or Protobuf with backward compatibility checks.
- **Dead letter queue from day one**: Events that fail processing after 3 retries go to DLQ. Without DLQ, failed events are silently dropped and data inconsistencies accumulate.

## Etched — Forge Enrichment Effectiveness (2026-02-08)

**Source**: `rune:forge` sessions across 5 plans
**Confidence**: MEDIUM (pattern observed, not yet quantified)

Forge enrichment adds genuine value for plans with security or performance implications. Across 5 plans:
- Security-focused plans: forge agents found 3-5 additional attack vectors per plan
- Performance-focused plans: forge agents identified caching opportunities and index recommendations
- Documentation-only plans: forge enrichment added minimal value (1-2 minor suggestions)

Recommendation: auto-trigger forge for plans with security or performance keywords. Skip for pure documentation changes.

## Traced — Unicode Handling in Search Queries (2026-02-15)

**Source**: rune:devise 20260215-search-unicode
**Confidence**: LOW (edge case, needs broader testing)

FTS5 with `tokenize='porter unicode61'` handles CJK characters but Porter stemming has no effect on non-Latin scripts. Search queries in Japanese or Chinese match on exact substrings only, not stemmed forms. Consider adding language-specific tokenizers for multilingual deployments.
