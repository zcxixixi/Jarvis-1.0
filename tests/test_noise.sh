#!/bin/bash
# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_PATH="$PROJECT_ROOT/.venv"

# Check if venv exists
if [ -d "$VENV_PATH" ]; then
    echo "🔋 Activating virtual environment..."
    source "$VENV_PATH/bin/activate"
else
    echo "⚠️  Virtual environment not found at $VENV_PATH"
    exit 1
fi

echo "🎧 Starting Noise Suppression Test..."
export PYTHONPATH="$SCRIPT_DIR"
python3 tests/test_noise_suppression.py
