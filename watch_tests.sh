#!/bin/bash
set -e

if ! command -v entr >/dev/null 2>&1; then
  echo "entr is required. Install with: brew install entr"
  exit 1
fi

# Find all python files, including those in subdirectories, and watch them
# The -c flag clears screen before each run
find . -name "*.py" | entr -c ./run_all_tests.sh
