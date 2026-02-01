"""
Query Router - 查询路由器
协调 S2S 和 ASR-Agent-TTS 两条处理路径
Now with semantic intent classification, context resolution, and latency optimizations!
"""
import asyncio
import logging
import os
import time
from typing import Optional, List
from .intent_classifier import IntentClassifier  # Keep as fallback
from .semantic_intent_classifier import get_semantic_classifier, SemanticIntentClassifier
from .context_resolver import get_context_resolver

logger = logging.getLogger(__name__)


# Transitional phrases for better UX during long operations
TRANSITION_PHRASES = {
    "weather": "正在获取天气数据",
    "stock": "正在查询实时行情",
    "finance": "正在查询金融数据",
    "search": "让我在网上搜索一下",
    "music": "正在准备音乐",
    "smart_home": "正在控制设备",
    "news": "正在获取最新新闻",
    "email": "正在准备发送邮件",
    "default": "正在处理您的请求，请稍候",
}


class QueryRouter:
    """查询路由器 - 根据意图选择处理路径 (Upgraded with Semantic AI + Latency Optimizations!)"""
    
    def __init__(self, hybrid_jarvis):
        """
        Args:
            hybrid_jarvis: HybridJarvis 实例（提供 S2S、Agent、TTS 访问）
        """
        self.jarvis = hybrid_jarvis
        
        # Lazy loading: Don't load classifiers on startup
        self._classifier = None
        self._context_resolver = None
        self._use_semantic = os.getenv("USE_SEMANTIC_CLASSIFIER", "true").lower() == "true"
        
        self.current_path: Optional[str] = None  # "s2s" or "agent"
        self._agent_lock = asyncio.Lock()  # 防止并发 Agent 调用
        
        logger.info(f"✅ QueryRouter initialized (semantic={'enabled' if self._use_semantic else 'disabled'}, lazy loading)")
    
    @property
    def classifier(self):
        """Lazy load classifier on first use"""
        if self._classifier is None:
            if self._use_semantic:
                try:
                    logger.info("🔄 Loading semantic classifier...")
                    start = time.time()
                    self._classifier = get_semantic_classifier()
                    elapsed = (time.time() - start) * 1000
                    logger.info(f"✅ Semantic classifier loaded in {elapsed:.0f}ms")
                except Exception as e:
                    logger.error(f"❌ Failed to load semantic classifier: {e}")
                    logger.info("⚠️ Falling back to keyword classifier")
                    self._classifier = IntentClassifier()
            else:
                self._classifier = IntentClassifier()
                logger.info("✅ Keyword classifier loaded")
        
        return self._classifier
    
    @property
    def context_resolver(self):
        """Lazy load context resolver on first use"""
        if self._context_resolver is None:
            # Only use context resolver with semantic classifier
            if isinstance(self.classifier, SemanticIntentClassifier):
                self._context_resolver = get_context_resolver()
                logger.info("✅ Context resolver loaded")
        
        return self._context_resolver
    
    async def route(self, transcription: str):
        """
        路由查询到合适的处理路径
        Now with context resolution, multi-intent detection, and performance monitoring!
        
        Args:
            transcription: ASR 转录文本
        """
        start_time = time.time()
        print(f"🚦 [ROUTER] route() called with: {transcription}")
        
        # Step 1: Resolve context (pronouns, references)
        t1 = time.time()
        resolved_text = transcription
        if self.context_resolver:
            resolved_text = self.context_resolver.resolve(transcription)
            if resolved_text != transcription:
                print(f"🔄 [ROUTER] Context resolved: {transcription} → {resolved_text}")
                logger.info(f"🔄 Context resolved: {transcription} → {resolved_text}")
        context_time = (time.time() - t1) * 1000
        
        # Step 2: Classify intent
        t2 = time.time()
        intent = self.classifier.classify(resolved_text)
        classify_time = (time.time() - t2) * 1000
        print(f"🚦 [ROUTER] Intent classified as: {intent}")
        
        # Step 3: Detect multiple intents (if using semantic classifier)
        intents = []
        if hasattr(self.classifier, 'detect_intents'):
            intents = self.classifier.detect_intents(resolved_text)
            if len(intents) > 1:
                print(f"🎯 [ROUTER] Multi-intent detected: {intents}")
                logger.info(f"🎯 Multi-intent query: {intents}")
        
        # Performance monitoring
        total_time = (time.time() - start_time) * 1000
        logger.info(f"⏱️ [PERF] Context: {context_time:.0f}ms, Classify: {classify_time:.0f}ms, Total: {total_time:.0f}ms")
        
        if total_time > 200:
            logger.warning(f"⚠️ [PERF] Slow routing: {total_time:.0f}ms")
        
        if total_time > 200:
            logger.warning(f"⚠️ [PERF] Slow routing: {total_time:.0f}ms")
        
        # Step 4: Route based on intent
        # 🔥 UNIFIED ARCHITECTURE REFACTOR (Phase 7)
        # Force ALL traffic to Agent. Deprecated S2S path.
        
        # 复杂查询：拦截 S2S，启动 Agent
        self.current_path = "agent"
        print(f"➔ [ROUTER] '{resolved_text}' → AGENT (Unified Path)")
        logger.info(f"🔀 [ROUTER] '{resolved_text}' → AGENT (Unified Path)")
        
        # Speak transitional phrase for better UX (only if complexity detected, otherwise silent)
        # For unified path, we might want to skip transitions for simple "hello" to be faster
        if intents and "conversation" not in intents:
             await self._speak_transition(intents[0])
        
        # 异步处理 Agent 路径
        asyncio.create_task(self._handle_agent_path(resolved_text, intents))
        
        # Step 5: Update context for next query
        if self.context_resolver:
            self.context_resolver.update_context(resolved_text, "agent")
    
    async def _speak_transition(self, intent: str):
        """
        Speak transitional phrase for better UX during long operations.
        
        Args:
            intent: Detected intent (e.g., "weather", "stock")
        """
        phrase = TRANSITION_PHRASES.get(intent, TRANSITION_PHRASES["default"])
        
        try:
            # Use quick TTS (non-blocking, fire-and-forget)
            if hasattr(self.jarvis, '_speak_quick'):
                await self.jarvis._speak_quick(phrase)
            else:
                # Fallback: log only
                logger.info(f"💬 [TRANSITION] Would say: {phrase}")
        except Exception as e:
            # Don't fail routing if transition fails
            logger.debug(f"[TRANSITION] Failed to speak: {e}")
    
    async def _handle_agent_path(self, transcription: str, intents: List[str] = None):
        """
        处理 Agent 路径
        
        Args:
            transcription: Resolved query text
            intents: List of detected intents (for multi-intent queries)
        """
        try:
            # 1. 拦截 S2S 音频
            await self.suppress_s2s_audio()
            
            # 2. 调用 Agent (使用 HybridJarvis 已经初始化好的 brain)
            async with self._agent_lock:
                print(f"🧠 [ROUTER] Calling Agent for: {transcription}")
                if intents:
                    print(f"   Intents: {intents}")
                logger.info(f"🧠 [AGENT] Processing: {transcription}")
                
                # Streaming Callback Wrapper
                async def on_token(token: str):
                    # Route to HybridJarvis streaming TTS handler
                    if hasattr(self.jarvis, '_speak_stream'):
                        await self.jarvis._speak_stream(token, is_final=False)
                
                # Call agent with streaming callback
                response = await self.jarvis.brain.run(transcription, stream_callback=on_token)
                
                # Flush any remaining buffer
                if hasattr(self.jarvis, '_speak_stream'):
                    await self.jarvis._speak_stream("", is_final=True)
                    
                print(f"💬 [ROUTER] Agent Response: {response[:50]}...")
                logger.info(f"💬 [AGENT] Response: {response[:50]}...")
            
            # 3. Use Bidirection TTS 播放响应 (Fallback if streaming failed/not used)
            # If streaming was used, this might be redundant, but _speak_v3 handles full text.
            # However, since we streamed it, we shouldn't speak it again!
            # BUT: If agent logic used tools and returned a final string WITHOUT streaming (e.g. tools don't stream),
            # we need to speak it.
            # Logic: If streaming happened, response was spoken. If not (e.g. tool result), we need to speak.
            # Since `agent.run` now supports mixed modes, we should check if we should speak the final result.
            # Best way: Rely on `on_token` to have spoken conversation. 
            # If `response` is just the final text, and we streamed it...
            pass # We streamed it! Don't speak again to avoid echo.
            
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
            # ✅ CRITICAL: Reset flags in finally block (per SKILL.md)
            # This ensures cleanup even if exceptions occur
            self.jarvis.self_speaking_mute = False
            self.jarvis.skip_cloud_response = False
            self.current_path = None
    
    def should_suppress_s2s(self) -> bool:
        """判断是否应该拦截 S2S 音频"""
        return self.current_path == "agent"
