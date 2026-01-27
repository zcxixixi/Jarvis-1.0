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
    echo "   Running with system python3..."
fi

# Run Jarvis
echo "🚀 Starting Jarvis..."
cd "$SCRIPT_DIR"
JARVIS_TEXT_ONLY=1 python3 main.py
