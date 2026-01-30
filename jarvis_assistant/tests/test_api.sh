#!/bin/bash
# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR" 
VENV_PATH="$PROJECT_ROOT/.venv"

# Check if venv exists
if [ -d "$VENV_PATH" ]; then
    echo "🔋 Activating virtual environment..."
    source "$VENV_PATH/bin/activate"
else
    echo "⚠️  Virtual environment not found at $VENV_PATH"
    # Try parent directory just in case
    if [ -d "../.venv" ]; then
         source "../.venv/bin/activate"
    fi
fi

echo "☁️  Running Cloud API Test..."
export PYTHONPATH="$PROJECT_ROOT"
python3 tests/test_doubao_api.py
