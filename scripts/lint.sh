#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
echo "=== black (check) ==="
python3 -m black --check --line-length 120 src/
echo "=== mypy ==="
python3 -m mypy --config-file pyproject.toml
echo "=== flake8 ==="
python3 -m flake8 --config .flake8 src/
echo "All checks passed."
