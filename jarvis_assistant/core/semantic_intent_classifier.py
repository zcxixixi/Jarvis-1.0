"""
Semantic Intent Classifier
Uses sentence embeddings for intelligent intent classification.
Replaces brittle keyword matching with semantic understanding.
"""
import json
import logging
import os
from typing import List, Dict, Tuple, Optional
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


class SemanticIntentClassifier:
    """
    Semantic intent classifier using sentence embeddings.
    
    Features:
    - Understands synonyms and paraphrasing
    - Multi-intent detection
    - Confidence scoring
    - Fallback to keyword matching
    """
    
    def __init__(
        self,
        model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2',
        intent_examples_path: Optional[str] = None,
        threshold: float = 0.6,
        use_cache: bool = True
    ):
        """
        Initialize semantic intent classifier.
        
        Args:
            model_name: Sentence transformer model name
            intent_examples_path: Path to intent examples JSON
            threshold: Similarity threshold for intent matching (0-1)
            use_cache: Whether to cache embeddings
        """
        logger.info(f"🧠 Initializing SemanticIntentClassifier with model: {model_name}")
        
        # Load sentence transformer model
        try:
            self.model = SentenceTransformer(model_name)
            logger.info(f"✅ Loaded model: {model_name}")
        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            raise
        
        self.threshold = threshold
        self.use_cache = use_cache
        
        # Load intent examples
        if intent_examples_path is None:
            # Default path
            config_dir = Path(__file__).parent.parent / "config"
            intent_examples_path = config_dir / "intent_examples.json"
        
        self.intent_examples = self._load_intent_examples(intent_examples_path)
        
        # Pre-compute embeddings for all intent examples
        self.intent_embeddings = self._precompute_embeddings()
        
        # Cache for query embeddings
        self.query_cache: Dict[str, np.ndarray] = {}
        
        # Simple patterns for fallback (from old classifier)
        self.SIMPLE_PATTERNS = [
            "你好", "早上好", "晚上好", "晚安", "再见",
            "几点", "星期几", "谢谢", "不客气",
            "讲个笑话", "怎么样"
        ]
        
        logger.info(f"✅ SemanticIntentClassifier initialized with {len(self.intent_examples)} intents")
    
    def _load_intent_examples(self, path: str) -> Dict:
        """Load intent examples from JSON file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                examples = json.load(f)
            logger.info(f"📚 Loaded {len(examples)} intent categories from {path}")
            return examples
        except Exception as e:
            logger.error(f"❌ Failed to load intent examples: {e}")
            # Return empty dict as fallback
            return {}
    
    def _precompute_embeddings(self) -> Dict[str, np.ndarray]:
        """Pre-compute embeddings for all intent examples."""
        logger.info("🔄 Pre-computing embeddings for intent examples...")
        
        embeddings = {}
        for intent, data in self.intent_examples.items():
            examples = data.get("examples", [])
            if examples:
                # Encode all examples for this intent
                intent_embeddings = self.model.encode(examples, convert_to_numpy=True)
                embeddings[intent] = intent_embeddings
                logger.debug(f"  {intent}: {len(examples)} examples encoded")
        
        logger.info(f"✅ Pre-computed embeddings for {len(embeddings)} intents")
        return embeddings
    
    def _get_query_embedding(self, text: str) -> np.ndarray:
        """Get embedding for query text (with caching)."""
        if self.use_cache and text in self.query_cache:
            return self.query_cache[text]
        
        embedding = self.model.encode([text], convert_to_numpy=True)[0]
        
        if self.use_cache:
            self.query_cache[text] = embedding
        
        return embedding
    
    def classify(self, text: str) -> str:
        """
        Classify query as 'simple' or 'complex'.
        
        Args:
            text: User query text
            
        Returns:
            "simple" - Simple conversation, use S2S
            "complex" - Complex query, use Agent
        """
        text = text.strip()
        
        # 1. Check simple patterns first (fast path)
        if any(pattern in text for pattern in self.SIMPLE_PATTERNS):
            logger.info(f"[SEMANTIC] '{text}' → SIMPLE (pattern match)")
            return "simple"
        
        # 2. Get semantic similarity scores
        intents = self.detect_intents(text)
        
        # 3. If any intent detected, it's complex
        if intents:
            logger.info(f"[SEMANTIC] '{text}' → COMPLEX (intents: {intents})")
            return "complex"
        
        # 4. Short queries default to simple
        if len(text) < 15:
            logger.info(f"[SEMANTIC] '{text}' → SIMPLE (short query)")
            return "simple"
        
        # 5. Default to complex for longer queries
        logger.info(f"[SEMANTIC] '{text}' → COMPLEX (default)")
        return "complex"
    
    def detect_intents(self, text: str, top_k: int = 3) -> List[str]:
        """
        Detect all intents in the query.
        
        Args:
            text: User query text
            top_k: Maximum number of intents to return
            
        Returns:
            List of detected intent names
        """
        if not self.intent_embeddings:
            logger.warning("No intent embeddings available")
            return []
        
        # Get query embedding
        query_embedding = self._get_query_embedding(text)
        
        # Calculate similarity with all intents
        intent_scores = []
        for intent, intent_embeds in self.intent_embeddings.items():
            # Calculate max similarity across all examples
            similarities = cosine_similarity([query_embedding], intent_embeds)[0]
            max_similarity = similarities.max()
            intent_scores.append((intent, max_similarity))
        
        # Sort by similarity
        intent_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Filter by threshold and get top_k
        detected = [
            intent for intent, score in intent_scores[:top_k]
            if score >= self.threshold
        ]
        
        if detected:
            scores_str = ", ".join([f"{i}:{s:.2f}" for i, s in intent_scores[:top_k]])
            logger.debug(f"[SEMANTIC] Intent scores: {scores_str}")
        
        return detected
    
    def get_confidence(self, text: str, intent: str) -> float:
        """
        Get confidence score for a specific intent.
        
        Args:
            text: User query text
            intent: Intent name to check
            
        Returns:
            Confidence score (0-1)
        """
        if intent not in self.intent_embeddings:
            return 0.0
        
        query_embedding = self._get_query_embedding(text)
        intent_embeds = self.intent_embeddings[intent]
        
        similarities = cosine_similarity([query_embedding], intent_embeds)[0]
        return float(similarities.max())
    
    def get_all_confidences(self, text: str) -> Dict[str, float]:
        """
        Get confidence scores for all intents.
        
        Args:
            text: User query text
            
        Returns:
            Dict mapping intent names to confidence scores
        """
        query_embedding = self._get_query_embedding(text)
        
        confidences = {}
        for intent, intent_embeds in self.intent_embeddings.items():
            similarities = cosine_similarity([query_embedding], intent_embeds)[0]
            confidences[intent] = float(similarities.max())
        
        return confidences
    
    def get_tools_for_intent(self, intent: str) -> List[str]:
        """Get tool names for a given intent."""
        if intent in self.intent_examples:
            return self.intent_examples[intent].get("tools", [])
        return []
    
    def clear_cache(self):
        """Clear query embedding cache."""
        self.query_cache.clear()
        logger.info("🗑️ Cleared query embedding cache")


# Singleton instance
_semantic_classifier: Optional[SemanticIntentClassifier] = None


def get_semantic_classifier(
    model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2',
    threshold: float = 0.6
) -> SemanticIntentClassifier:
    """
    Get the global semantic classifier instance.
    
    Args:
        model_name: Sentence transformer model name
        threshold: Similarity threshold
        
    Returns:
        SemanticIntentClassifier instance
    """
    global _semantic_classifier
    
    if _semantic_classifier is None:
        _semantic_classifier = SemanticIntentClassifier(
            model_name=model_name,
            threshold=threshold
        )
    
    return _semantic_classifier


# Quick test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Initialize classifier
    classifier = SemanticIntentClassifier()
    
    # Test queries
    test_queries = [
        "天气怎么样",
        "查一下北京的天气",
        "今天会下雨吗",
        "特斯拉股价",
        "帮我看看苹果公司的股票",
        "播放音乐",
        "我想听歌",
        "打开客厅的灯",
        "北京天气怎么样，顺便查下特斯拉股价",  # Multi-intent
        "你好",
        "现在几点",
    ]
    
    print("\n" + "="*60)
    print("Semantic Intent Classifier Test")
    print("="*60 + "\n")
    
    for query in test_queries:
        classification = classifier.classify(query)
        intents = classifier.detect_intents(query)
        confidences = classifier.get_all_confidences(query)
        
        print(f"Query: {query}")
        print(f"  Classification: {classification}")
        print(f"  Detected Intents: {intents}")
        if intents:
            print(f"  Confidence Scores:")
            for intent in intents:
                print(f"    {intent}: {confidences[intent]:.3f}")
        print()
