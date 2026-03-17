#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
echo "=== black (reformat) ==="
python3 -m black --line-length 120 src/
echo "Done."
