#!/usr/bin/env python3
"""
完整重写 QueryRouter 的并发控制部分
确保语法正确，逻辑清晰
"""

import sys

file_path = "/Users/kaijimima1234/Desktop/jarvis/jarvis_assistant/core/query_router.py"

# 读取原始文件
with open(file_path, 'r') as f:
    lines = f.readlines()

# 找到 __init__ 方法并添加必要的属性
new_lines = []
in_init = False
init_done = False

for i, line in enumerate(lines):
    # 检测 __init__ 方法
    if 'def __init__(self, hybrid_jarvis):' in line:
        in_init = True
        new_lines.append(line)
        continue
    
    # 在 __init__ 结束前（logger.info 之后）添加新属性
    if in_init and not init_done and 'logger.info(f"✅ QueryRouter initialized' in line:
        # 在这行之前插入新属性
        new_lines.append('        \n')
        new_lines.append('        # [FIX] Concurrency control\n')
        new_lines.append('        self._processing_lock = asyncio.Lock()\n')
        new_lines.append('        self.is_processing = False\n')
        new_lines.append('        self._last_processed_text = ""\n')
        new_lines.append('        self._last_processed_time = 0\n')
        new_lines.append('        \n')
        init_done = True
        new_lines.append(line)
        in_init = False
        continue
    
    new_lines.append(line)

# 写回文件
with open(file_path, 'w') as f:
    f.writelines(new_lines)

print("✅ Step 1: Added concurrency attributes to __init__")

# 现在重写 route() 方法
with open(file_path, 'r') as f:
    content = f.read()

# 找到 route 方法并替换
import re

# 找到方法定义
route_pattern = r'    async def route\(self, transcription: str\):.*?(?=\n    (?:async )?def )'
match = re.search(route_pattern, content, re.DOTALL)

if not match:
    print("ERROR: Could not find route method")
    sys.exit(1)

# 新的 route 方法实现
new_route_method = '''    async def route(self, transcription: str):
        """路由查询到合适的处理路径"""
        if not transcription or not transcription.strip():
            return
        
        # Deduplication
        import time
        now = time.time()
        if transcription == self._last_processed_text and (now - self._last_processed_time) < 2.0:
            logger.info(f"🛑 [ROUTER] Ignoring duplicate: {transcription}")
            return
        
        # Concurrency lock
        if self.is_processing:
            logger.warning(f"🛑 [ROUTER] Busy! Dropping: {transcription}")
            return
        
        async with self._processing_lock:
            try:
                self.is_processing = True
                self._last_processed_text = transcription
                self._last_processed_time = now
                
                print(f"\\n🚦 [ROUTER] route() called with: {transcription}")
                
                # Classify intent
                intent = self.classifier.classify(transcription)
                print(f"🚦 [ROUTER] Intent classified as: {intent}")
                
                # Route to Agent (unified architecture)
                print(f"➔ [ROUTER] '{transcription}' → AGENT (Unified Path)")
                self.current_path = "agent"
                
                # Get intents list if available
                intents = []
                if hasattr(self.classifier, 'detect_intents'):
                    intents = self.classifier.detect_intents(transcription)
                
                await self._handle_agent_path(transcription, intents)
                    
            except Exception as e:
                logger.error(f"❌ [ROUTER] Error: {e}", exc_info=True)
            finally:
                self.is_processing = False
    
'''

# 替换
new_content = content[:match.start()] + new_route_method + content[match.end():]

with open(file_path, 'w') as f:
    f.write(new_content)

print("✅ Step 2: Rewrote route() method with proper indentation")
print("✅ QueryRouter修复完成")
