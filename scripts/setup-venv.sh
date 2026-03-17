#!/bin/bash
# Create and setup Python virtual environment

set -e

cd "$(dirname "$0")/.."

VENV_DIR="${1:-.venv}"

echo "Creating virtual environment in $VENV_DIR..."
python3 -m venv "$VENV_DIR"

echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "Virtual environment setup complete!"
echo "To activate: source $VENV_DIR/bin/activate"
