#!/bin/bash
# Jarvis 启动脚本 - 自动配置 PYTHONPATH

cd "$(dirname "$0")"

echo "🚀 启动 Jarvis..."
echo "📁 项目路径: $(pwd)"

# 设置 PYTHONPATH
export PYTHONPATH="$(pwd):$PYTHONPATH"

# 启动 Jarvis
./venv/bin/python3 jarvis_assistant/core/hybrid_jarvis.py "$@"
