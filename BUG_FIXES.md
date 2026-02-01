# Bug 修复记录

## 🐛 发现的问题

**症状:** 用户只听到 "正在获取天气"，但没听到实际的天气结果

**根本原因:** Agent 返回的文本没有被发送到 TTS

**日志证据:**
```
💬 [ROUTER] Agent Response: 抱歉，我没有找到 Beijing, China 的位置。...
📥 [TTS INPUT] Received chunk: '' (final=True)  ← 空字符串！
```

---

## ✅ 修复内容

**修改文件:** `query_router.py`

**修改位置:** `_handle_agent_path` 方法

**修复逻辑:**

之前（Bug）:
```python
# 200-218行
await self.jarvis._speak_stream("", is_final=True)  # 发送空字符串
pass # We streamed it! Don't speak again to avoid echo.
```

现在（修复后）:
```python
# 确保 Agent 返回的文本被输出
if response and response.strip():
    print(f"🔊 [ROUTER] Speaking final response via TTS")
    if hasattr(self.jarvis, '_speak_v3'):
        await self.jarvis._speak_v3(response)
    elif hasattr(self.jarvis, '_speak_stream'):
        await self.jarvis._speak_stream(response, is_final=True)
```

---

## 🧪 测试验证

**重新测试步骤:**

1. 启动 Jarvis: `./run_jarvis.sh`
2. 查看日志: `tail -f jarvis.log`
3. 说话: "嘿 Jarvis" → "查询一下当前的天气"

**预期日志:**
```
============================================================
👤 [USER INPUT] 查询一下当前的天气
============================================================

💬 [ROUTER] Agent Response: 抱歉，我没有找到 Beijing...
🔊 [ROUTER] Speaking final response via TTS  ← 新增
🔈 [TTS OUTPUT] Synthesizing: '抱歉，我没有找到...'  ← 应该有内容
🔌 [TTS POOL] Connection status before: CLOSED/OPEN
🔌 [TTS POOL] Connection status after: NEW/REUSED
🎵 [TTS COMPLETE] Sent XX audio chunks
```

**预期结果:** 能听到完整的回复

---

## 📊 Phase 1 状态

### 修复的 Bug
1. ✅ `NameError: SemanticIntentClassifier not defined`
2. ✅ `RuntimeError: no running event loop` (asyncio.create_task)
3. ✅ **Agent 响应不输出到 TTS** (当前修复)

### 待验证
- [ ] TTS 连接池是否正常工作（REUSED 状态）
- [ ] 多次对话延迟改善
- [ ] 音质正常

---

**当前版本:** Phase 1 集成 v1.3 (Bug 修复)

**下次测试:** 请说 3 次不同的话，验证连接池复用
