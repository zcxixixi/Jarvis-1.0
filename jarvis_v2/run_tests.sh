#!/bin/bash
# Updated test runner using existing venv

cd "$(dirname "$0")"

# Use existing venv from main jarvis project
PYTHON="../venv/bin/python3"

if [ ! -f "$PYTHON" ]; then
    echo "❌ Virtual environment not found at ../venv"
    echo "Please ensure jarvis venv is set up"
    exit 1
fi

echo "╔══════════════════════════════════════════════════════════╗"
echo "║                                                          ║"
echo "║          JARVIS V2 MODULE TESTING SUITE                 ║"
echo "║                                                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "Using Python: $PYTHON"
echo ""

PASSED=0
FAILED=0

run_test() {
    local test_name="$1"
    local test_file="$2"
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Running: $test_name"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if $PYTHON "$test_file"; then
        echo "✅ $test_name PASSED"
        ((PASSED++))
    else
        echo "❌ $test_name FAILED"
        ((FAILED++))
    fi
}

# Run each test
run_test "VAD Module" "tests/test_vad_simple.py"
run_test "Wake Word Module" "tests/test_wake_word_simple.py"

# AudioIO test requires user interaction (microphone)
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚠️  AudioIO Test (requires microphone - run manually)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "To test AudioIO: $PYTHON tests/test_audio_io_simple.py"

# Summary
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                    TEST SUMMARY                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "✅ Passed: $PASSED"
echo "❌ Failed: $FAILED"  
echo ""

if [ $FAILED -eq 0 ]; then
    echo "🎉 ALL AUTOMATED TESTS PASSED!"
    echo ""
    echo "Next steps:"
    echo "1. Test AudioIO manually: $PYTHON tests/test_audio_io_simple.py"
    echo "2. Run full system: $PYTHON main.py"
    exit 0
else
    echo "⚠️  Some tests failed. Please review errors above."
    exit 1
fi
