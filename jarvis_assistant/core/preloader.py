"""
Semantic Classifier Preloader
Background task to preload semantic classifier for zero perceived latency.
"""
import asyncio
import logging
import time

logger = logging.getLogger(__name__)


async def preload_semantic_classifier():
    """
    Preload semantic classifier in background for zero perceived latency.
    Runs after system stabilizes (~2s), loads model while user is idle.
    
    This is a fire-and-forget task that doesn't block startup.
    """
    try:
        # Wait for system to stabilize
        await asyncio.sleep(2)
        
        logger.info("🔄 [PRELOAD] Starting background preload of semantic classifier...")
        start = time.time()
        
        # Import and initialize semantic classifier
        from jarvis_assistant.core.semantic_intent_classifier import get_semantic_classifier
        get_semantic_classifier()
        
        elapsed = (time.time() - start) * 1000
        logger.info(f"✅ [PRELOAD] Semantic classifier ready in {elapsed:.0f}ms")
        print(f"✅ [PRELOAD] Semantic classifier preloaded in {elapsed:.0f}ms")
        
    except Exception as e:
        # Don't fail if preload fails - lazy loading will handle it
        logger.warning(f"⚠️ [PRELOAD] Failed to preload semantic classifier: {e}")
        logger.info("💡 [PRELOAD] Will load on first use instead")
        print(f"⚠️ [PRELOAD] Preload failed, will lazy load: {e}")


def start_preloading():
    """
    Start preloading task in background.
    Call this from hybrid_jarvis.__init__() after router initialization.
    """
    asyncio.create_task(preload_semantic_classifier())
    logger.info("🚀 [PRELOAD] Background preloading task started")
