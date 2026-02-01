#!/bin/bash
# 快速启动 Jarvis（修复后版本）

cd "$(dirname "$0")"

echo "🚀 启动 Jarvis (Phase 1: TTS 连接池优化版)"
echo "="*60

# 停止旧进程
pkill -9 -f "hybrid_jarvis.py" 2>/dev/null
sleep 1

# 启动新进程
PYTHONPATH="$(pwd):$PYTHONPATH" ./venv/bin/python3 jarvis_assistant/core/hybrid_jarvis.py > jarvis.log 2>&1 &
PID=$!
echo $PID > jarvis.pid

echo "✅ Jarvis 已启动 (PID: $PID)"
echo "📝 日志文件: jarvis.log"
echo ""
echo "📊 查看实时日志:"
echo "   tail -f jarvis.log"
echo ""
echo "🛑 停止 Jarvis:"
echo "   pkill -f hybrid_jarvis.py"
echo ""

# 等待启动
sleep 8

# 检查状态
if ps -p $PID > /dev/null; then
    echo "✅ Jarvis 运行正常！"
    echo ""
    echo "最近日志:"
    tail -20 jarvis.log | grep -E "(TTS Singleton|Connected|alive)"
else
    echo "❌ Jarvis 启动失败，查看日志:"
    tail -30 jarvis.log
fi
