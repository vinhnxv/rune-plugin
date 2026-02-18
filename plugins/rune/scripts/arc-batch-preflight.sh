#!/bin/bash
set -euo pipefail

# ──────────────────────────────────────────────
# arc-batch-preflight.sh — Pre-validate plan files
# Reads plan paths from stdin, validates each, writes validated list to stdout
# ──────────────────────────────────────────────

ERRORS=0
SEEN=()

while IFS= read -r plan || [[ -n "$plan" ]]; do
  [[ -z "$plan" || "$plan" == \#* ]] && continue

  # 1. File exists
  if [[ ! -f "$plan" ]]; then
    echo "ERROR: Plan file not found: $plan" >&2
    ERRORS=$((ERRORS + 1))
    continue
  fi

  # 2. Not a symlink (arc rejects symlinks)
  if [[ -L "$plan" ]]; then
    echo "ERROR: Symlink rejected: $plan" >&2
    ERRORS=$((ERRORS + 1))
    continue
  fi

  # 3. Path traversal check
  if [[ "$plan" == *".."* ]]; then
    echo "ERROR: Path traversal rejected: $plan" >&2
    ERRORS=$((ERRORS + 1))
    continue
  fi

  # 4. Non-empty file check
  if [[ ! -s "$plan" ]]; then
    echo "ERROR: Empty plan file: $plan" >&2
    ERRORS=$((ERRORS + 1))
    continue
  fi

  # 5. Canonicalize path
  CANONICAL=$(realpath "$plan" 2>/dev/null || echo "$plan")

  # 6. Duplicate check
  DUPLICATE=false
  for seen_path in "${SEEN[@]+"${SEEN[@]}"}"; do
    if [[ "$seen_path" == "$CANONICAL" ]]; then
      echo "WARNING: Duplicate plan skipped: $plan" >&2
      DUPLICATE=true
      break
    fi
  done

  if ! $DUPLICATE; then
    SEEN+=("$CANONICAL")
    echo "$plan"
  fi
done

if [[ $ERRORS -gt 0 ]]; then
  echo "Pre-flight: $ERRORS error(s) found" >&2
  exit 1
fi
