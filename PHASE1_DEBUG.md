# Phase 1 调试指南

## 🔍 新增的调试打印

现在 `hybrid_jarvis.py` 会打印完整的输入输出流：

### 1. 用户输入
```
============================================================
👤 [USER INPUT] 你好
============================================================
```

### 2. TTS 文本接收
```
📥 [TTS INPUT] Received chunk: '你好' (final=False)
📥 [TTS INPUT] Received chunk: '！' (final=False)
```

### 3. TTS 连接池状态
```
🔌 [TTS POOL] Connection status before: OPEN ✅
🔌 [TTS POOL] Connection status after: REUSED ✅
```
**或者首次连接:**
```
🔌 [TTS POOL] Connection status before: CLOSED ⚠️
🔌 [TTS POOL] Connection status after: NEW 🆕
```

### 4. TTS 输出
```
🔈 [TTS OUTPUT] Synthesizing: '你好！'
🎵 [TTS COMPLETE] Sent 15 audio chunks to speaker queue
```

---

## 🧪 运行测试

```bash
cd /Users/kaijimima1234/Desktop/jarvis
./start_jarvis.sh

# 然后说话或输入:
# "嘿 Jarvis" → "你好"
# "嘿 Jarvis" → "现在几点"
# "嘿 Jarvis" → "天气怎么样"
```

---

## ✅ 验证连接池工作

查看日志中的 **连接状态**：

**第 1 次对话** (应该显示):
```
🔌 [TTS POOL] Connection status before: CLOSED ⚠️
🔌 [TTS POOL] Connection status after: NEW 🆕
```

**第 2 次对话** (应该显示):
```
🔌 [TTS POOL] Connection status before: OPEN ✅
🔌 [TTS POOL] Connection status after: REUSED ✅
```

**第 3 次对话** (应该显示):
```
🔌 [TTS POOL] Connection status before: OPEN ✅
🔌 [TTS POOL] Connection status after: REUSED ✅
```

如果每次都显示 `NEW 🆕` → 连接池未生效，需要调试

---

## 🐛 如果发现 Bug

日志会显示:
```
❌ [TTS ERROR] Stream TTS failed: [错误信息]
```

请复制完整的错误信息以便诊断。
