#!/bin/bash
# 完全停止并重启 Jarvis

cd "$(dirname "$0")"

echo "🛑 停止所有 Jarvis 进程..."
pkill -9 -f "hybrid_jarvis.py" 2>/dev/null || true
pkill -9 -f "start_jarvis.sh" 2>/dev/null || true
pkill -9 -f "run_jarvis.sh" 2>/dev/null || true
sleep 2

# 确认清理完成
if ps aux | grep -E "hybrid_jarvis" | grep -v grep >/dev/null; then
    echo "❌ 警告：仍有进程在运行"
    ps aux | grep -E "hybrid_jarvis" | grep -v grep
    exit 1
fi

echo "✅ 所有进程已停止"
echo ""
echo "🚀 启动 Jarvis..."
echo ""

# 设置 PYTHONPATH（关键！）
export PYTHONPATH="$(pwd):$PYTHONPATH"

# 启动新进程
./venv/bin/python3 jarvis_assistant/core/hybrid_jarvis.py > jarvis.log 2>&1 &
PID=$!
echo $PID > jarvis.pid

sleep 5

# 检查启动状态
if ps -p $PID > /dev/null; then
    echo "✅ Jarvis 启动成功 (PID: $PID)"
    echo ""
    echo "📊 查看日志:"
    echo "   tail -f jarvis.log"
    echo ""
    echo "🛑 停止 Jarvis:"
    echo "   pkill -f hybrid_jarvis.py"
    echo ""
    tail -15 jarvis.log
else
    echo "❌ Jarvis 启动失败"
    echo "查看错误日志:"
    tail -30 jarvis.log
    exit 1
fi
