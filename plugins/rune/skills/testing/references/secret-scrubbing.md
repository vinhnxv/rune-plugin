# Secret Scrubbing — Test Output Redaction

Redact secrets from test output before passing to AI agent context.
Applied to ALL test runner output (unit, integration, E2E) before ingestion.

## scrubSecrets(text) Algorithm

```javascript
function scrubSecrets(text) {
  if (!text || typeof text !== 'string') return text

  const patterns = [
    // AWS credentials
    [/AKIA[0-9A-Z]{16}/g, '[REDACTED:AWS_ACCESS_KEY]'],
    [/(?:AWS_SECRET_ACCESS_KEY|aws_secret_access_key)\s*[=:]\s*\S+/gi, '[REDACTED:AWS_SECRET]'],

    // Generic API keys and tokens
    [/(?:API_KEY|APIKEY|api_key)\s*[=:]\s*\S+/gi, '[REDACTED:API_KEY]'],
    [/(?:SECRET_KEY|SECRET|secret_key)\s*[=:]\s*\S+/gi, '[REDACTED:SECRET]'],
    [/(?:ACCESS_TOKEN|access_token)\s*[=:]\s*\S+/gi, '[REDACTED:TOKEN]'],
    [/(?:AUTH_TOKEN|auth_token)\s*[=:]\s*\S+/gi, '[REDACTED:TOKEN]'],

    // Bearer tokens
    [/Bearer\s+[A-Za-z0-9\-._~+\/]+=*/g, 'Bearer [REDACTED]'],

    // OpenAI / Anthropic keys
    [/sk-[A-Za-z0-9]{20,}/g, '[REDACTED:SK_KEY]'],
    [/sk-ant-[A-Za-z0-9\-]{20,}/g, '[REDACTED:ANTHROPIC_KEY]'],

    // GitHub tokens
    [/ghp_[A-Za-z0-9]{36,}/g, '[REDACTED:GH_PAT]'],
    [/gho_[A-Za-z0-9]{36,}/g, '[REDACTED:GH_OAUTH]'],
    [/ghs_[A-Za-z0-9]{36,}/g, '[REDACTED:GH_APP]'],
    [/github_pat_[A-Za-z0-9_]{82,}/g, '[REDACTED:GH_PAT_V2]'],

    // JWT tokens (header.payload.signature)
    [/eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}/g, '[REDACTED:JWT]'],

    // Generic password/secret patterns in env vars
    [/(?:PASSWORD|PASSWD|DB_PASS)\s*[=:]\s*\S+/gi, '[REDACTED:PASSWORD]'],
    [/(?:DATABASE_URL|REDIS_URL|MONGO_URI)\s*[=:]\s*\S+/gi, '[REDACTED:CONNECTION_STRING]'],

    // Private keys (PEM format opening line)
    [/-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----/g, '[REDACTED:PRIVATE_KEY_HEADER]'],

    // Email addresses (optional — reduce noise in test output)
    [/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g, '[REDACTED:EMAIL]'],

    // Env var assignments matching common secret patterns
    [/^(?:export\s+)?(?:\w*(?:KEY|SECRET|TOKEN|PASSWORD|CREDENTIAL)\w*)\s*=\s*\S+/gmi, '[REDACTED:ENV_SECRET]'],
  ]

  let scrubbed = text
  for (const [pattern, replacement] of patterns) {
    scrubbed = scrubbed.replace(pattern, replacement)
  }
  return scrubbed
}
```

## Usage

Call `scrubSecrets()` on test output before:
1. Injecting into agent prompt context
2. Writing to artifact files that agents will read
3. Passing to failure analyst for root cause analysis

```javascript
// In arc-phase-test.md STEP 5-7, after reading tier results:
const rawOutput = Read(`tmp/arc/${id}/test-results-unit.md`)
const scrubbedOutput = scrubSecrets(rawOutput)
// Pass scrubbedOutput to failure analyst, not rawOutput
```

## Truncation (complementary defense)

Secret scrubbing works alongside output truncation:
- **500-line ceiling** for AI agent context
- **Full output** written to artifact file (contains secrets — not agent-visible)
- **Summary** (last 20-50 lines) extracted for agent context

Truncation is defense-in-depth — not a substitute for scrubbing.

## Patterns NOT Scrubbed (by design)

- Test assertion values (may look like secrets but are test data)
- File paths (validated by SAFE_PATH_PATTERN separately)
- Port numbers (needed for debugging service startup)
- Error codes and HTTP status codes (needed for failure analysis)
