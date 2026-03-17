#!/bin/bash
# Run all tests for pyapple2

set -e

cd "$(dirname "$0")/.."

echo "Running all tests..."
cd src
python run_tests.py
