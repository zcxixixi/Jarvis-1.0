#!/bin/bash
# Jarvis Universal Test Runner

echo "============================================================"
echo "🚀 JARVIS INTEGRATION PIPELINE"
echo "============================================================"

# 0. Activate Virtual Environment
if [ -d ".venv" ]; then
    echo "🐍 Activating virtual environment (.venv)..."
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "🐍 Activating virtual environment (venv)..."
    source venv/bin/activate
fi

# 1. Syntax Check
echo "🔍 Checking Python Syntax..."
python3 -m py_compile jarvis_assistant/*.py jarvis_assistant/core/*.py jarvis_assistant/services/*.py jarvis_assistant/utils/*.py
if [ $? -eq 0 ]; then
    echo "✅ Syntax Check Passed"
else
    echo "❌ Syntax Check Failed"
    exit 1
fi

# 2. Text-Based Tool & Agent Tests
echo -e "\n🔧 Running Text-Based Tool & Agent Tests..."
python3 -u jarvis_assistant/tests/dialogue_auto_check.py
if [ $? -eq 0 ]; then
    echo "✅ Text-Based Tests Passed"
else
    echo "❌ Text-Based Tests Failed"
    exit 1
fi


# 3. Environment Check
echo -e "\nenv Checking Environment Configuration..."
if [ -f "jarvis_assistant/.env" ]; then
    echo "✅ .env file found"
else
    echo "⚠️ .env file missing in jarvis_assistant/"
fi

echo -e "\n============================================================"
echo "🎉 ALL TESTS PASSED"
echo "============================================================"
echo -e "\n💡 Tip: Use 'fswatch' or 'entr' to run this efficiently on file change:"
echo "   ls **/*.py | entr -c ./run_all_tests.sh"
