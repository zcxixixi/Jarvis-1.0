# 如何运行 Jarvis (Phase 1 优化版)

## 🚀 启动 Jarvis

### 方法 1: 快速启动（推荐）

```bash
cd /Users/kaijimima1234/Desktop/jarvis
./run_jarvis.sh
```

### 方法 2: 手动启动

```bash
cd /Users/kaijimima1234/Desktop/jarvis

# 停止旧进程
pkill -f hybrid_jarvis.py

# 启动新进程
./start_jarvis.sh > jarvis.log 2>&1 &
```

---

## 📊 查看日志

### 实时查看（推荐）

```bash
tail -f jarvis.log
```

按 `Ctrl+C` 停止查看（不会停止 Jarvis）

### 查看最新 50 行

```bash
tail -50 jarvis.log
```

### 只看用户输入和 TTS 状态

```bash
grep -E "(USER INPUT|TTS POOL|TTS OUTPUT)" jarvis.log
```

---

## 🎤 使用 Jarvis

### 语音对话

1. 说 "嘿 Jarvis" (唤醒)
2. 等待唤醒音
3. 说出你的问题，例如：
   - "你好"
   - "现在几点"
   - "天气怎么样"

### 键盘输入

直接在终端输入文本（如果 TEXT_ONLY 模式启用）

---

## 🔍 验证连接池工作

查看日志中是否出现：

**首次对话:**
```
🔌 [TTS POOL] Connection status before: CLOSED ⚠️
🔌 [TTS POOL] Connection status after: NEW 🆕
```

**后续对话:**
```
🔌 [TTS POOL] Connection status before: OPEN ✅
🔌 [TTS POOL] Connection status after: REUSED ✅  ← 这个说明连接池生效！
```

---

## 🛑 停止 Jarvis

```bash
pkill -f hybrid_jarvis.py
```

或者：

```bash
kill $(cat jarvis.pid)
```

---

## 🐛 故障排查

### 问题 1: 看到 NameError

**症状:**
```
NameError: name 'SemanticIntentClassifier' is not defined
```

**解决:**
```bash
# 确保使用最新代码
git status
pkill -f hybrid_jarvis.py
./run_jarvis.sh
```

### 问题 2: 没有声音

**检查:**
1. 音量是否打开
2. 扬声器是否连接
3. 查看日志中是否有 `[TTS OUTPUT]`

### 问题 3: 看不到调试信息

**确保查看正确的日志文件:**
```bash
# 正确 ✅
tail -f jarvis.log

# 错误 ❌ (旧文件)
tail -f jarvis_debug_detailed.log
```

---

## ✅ 当前状态

运行以下命令检查 Jarvis 是否运行：

```bash
ps aux | grep hybrid_jarvis.py | grep -v grep
```

如果有输出 → Jarvis 正在运行 ✅  
如果无输出 → Jarvis 未运行 ❌

---

## 📂 文件说明

| 文件 | 说明 |
|------|------|
| `run_jarvis.sh` | **快速启动脚本**（推荐使用） |
| `start_jarvis.sh` | 基础启动脚本 |
| `jarvis.log` | **当前运行日志**（查看这个！） |
| `jarvis.pid` | 进程 ID 文件 |
| `PHASE1_VALIDATION.md` | 验证清单 |
| `PHASE1_DEBUG.md` | 调试指南 |

---

现在 Jarvis 应该正在运行！

**下一步:** 说 "嘿 Jarvis" 测试，然后查看 `jarvis.log` 中的调试输出！
