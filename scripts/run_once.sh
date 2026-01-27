#!/bin/bash
set -e

if [ -z "$1" ]; then
  echo "Usage: bash run_once.sh \"你的问题\""
  exit 1
fi

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

printf "%s\n" "$1" | JARVIS_TEXT_ONLY=1 JARVIS_ALLOW_STDIN_PIPE=1 python3 hybrid_jarvis.py
