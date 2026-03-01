#!/bin/bash
# Regenerate Rune output for Storybook comparison.
# Usage: ./refresh.sh [figma-url]
#
# Default URL is the Sign Up design (node 12-749).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FIGMA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

DEFAULT_URL="https://www.figma.com/design/VszzNQxbig1xYxHTrfxeIY/50-Web-Sign-up-log-in-designs--Community-?node-id=12-749"
URL="${1:-$DEFAULT_URL}"

echo "Generating Rune output from: $URL"
cd "$FIGMA_DIR"
python3 cli.py react "$URL" --code > "$SCRIPT_DIR/src/rune-output/SignUp.tsx"
echo "Wrote storybook/src/rune-output/SignUp.tsx"
