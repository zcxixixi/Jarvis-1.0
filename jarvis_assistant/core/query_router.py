"""
Query Router - 查询路由器
协调 S2S 和 ASR-Agent-TTS 两条处理路径
"""
import asyncio
import logging
from typing import Optional
from .intent_classifier import IntentClassifier

logger = logging.getLogger(__name__)


class QueryRouter:
    """查询路由器 - 根据意图选择处理路径"""
    
    def __init__(self, hybrid_jarvis):
        """
        Args:
            hybrid_jarvis: HybridJarvis 实例（提供 S2S、Agent、TTS 访问）
        """
        self.jarvis = hybrid_jarvis
        self.classifier = IntentClassifier()
        self.current_path: Optional[str] = None  # "s2s" or "agent"
        self._agent_lock = asyncio.Lock()  # 防止并发 Agent 调用
        
        logger.info("QueryRouter initialized")
    
    async def route(self, transcription: str):
        """
        路由查询到合适的处理路径
        
        Args:
            transcription: ASR 转录文本
        """
        print(f"🚦 [ROUTER] route() called with: {transcription}")
        intent = self.classifier.classify(transcription)
        print(f"🚦 [ROUTER] Intent classified as: {intent}")
        
        if intent == "simple":
            # 简单查询：S2S 已经在处理，无需额外操作
            self.current_path = "s2s"
            print(f"➔ [ROUTER] '{transcription}' -> S2S (fast path)")
            logger.info(f"🔀 [ROUTER] '{transcription}' -> S2S (fast path)")
            
        elif intent == "complex":
            # 复杂查询：拦截 S2S，启动 Agent
            self.current_path = "agent"
            print(f"➔ [ROUTER] '{transcription}' -> AGENT (deep path)")
            logger.info(f"🔀 [ROUTER] '{transcription}' -> AGENT (deep path)")
            
            # 异步处理 Agent 路径，避免阻塞
            asyncio.create_task(self._handle_agent_path(transcription))
    
    async def _handle_agent_path(self, transcription: str):
        """处理 Agent 路径"""
        try:
            # 1. 拦截 S2S 音频
            await self.suppress_s2s_audio()
            
            # 2. 调用 Agent (使用 HybridJarvis 已经初始化好的 brain)
            async with self._agent_lock:
                print(f"🧠 [ROUTER] Calling Agent for: {transcription}")
                logger.info(f"🧠 [AGENT] Processing: {transcription}")
                
                # 直接调用 jarvis.brain，避免重新加载 31 个插件
                response = await self.jarvis.brain.run(transcription)
                print(f"💬 [ROUTER] Agent Response: {response[:50]}...")
                logger.info(f"💬 [AGENT] Response: {response[:50]}...")
            
            # 3. 使用 Bidirection TTS 播放响应
            print(f"🔊 [ROUTER] Handover to TTS: {response[:50]}...")
            await self.speak_with_tts(response)
            print("✅ [ROUTER] Agent Path completed")
            
        except Exception as e:
            logger.error(f"❌ [AGENT PATH] Error: {e}", exc_info=True)
            # 降级到 S2S
            self.current_path = "s2s"
    
    async def suppress_s2s_audio(self):
        """拦截 S2S 音频输出"""
        logger.info("🔇 [ROUTER] Suppressing S2S audio")
        
        # 清空 speaker_queue
        if hasattr(self.jarvis, 'speaker_queue'):
            while not self.jarvis.speaker_queue.empty():
                try:
                    self.jarvis.speaker_queue.get_nowait()
                except:
                    break
        
        # 设置静音标志 (控制播放)
        self.jarvis.skip_cloud_response = True
        # 同时设置回声消除标志 (控制麦克风)
        self.jarvis.self_speaking_mute = True
    
    async def speak_with_tts(self, text: str):
        """使用 HybridJarvis 的 _speak_v3 播放文本 (统一使用已验证工作的路径)"""
        logger.info(f"🔊 [TTS] Redirecting to _speak_v3: {text[:50]}...")
        
        try:
            # 直接调用 jarvis 的 _speak_v3
            # 这会自动处理 "agent" 标签和正确的 V1 Binary 协议
            # 注意：_speak_v3 是异步生成多段音频的，但由于它内部是异步循环，我们需要 await 它
            await self.jarvis._speak_v3(text)
            
            logger.info("✅ [TTS] Playback complete via _speak_v3")
            
        except Exception as e:
            logger.error(f"❌ [TTS] Error in _speak_v3 handoff: {e}", exc_info=True)
        finally:
            # 恢复环境标志
            self.jarvis.self_speaking_mute = False
            self.jarvis.skip_cloud_response = False  # [FIX] Reset here after Agent completes
            self.current_path = None
    
    def should_suppress_s2s(self) -> bool:
        """判断是否应该拦截 S2S 音频"""
        return self.current_path == "agent"
