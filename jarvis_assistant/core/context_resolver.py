"""
Context Resolver
Resolves pronouns and references using conversation context.
Enables Jarvis to understand "它", "那里", "这个" etc.
"""
import logging
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Entity:
    """Represents an entity mentioned in conversation."""
    type: str  # "stock", "location", "person", "device", etc.
    value: str  # The actual entity value
    mentioned_at: datetime = field(default_factory=datetime.now)
    context: str = ""  # The query where it was mentioned


class ContextResolver:
    """
    Resolves context-dependent references in queries.
    
    Features:
    - Track entities (stocks, locations, devices, etc.)
    - Resolve pronouns ("它" → last mentioned entity)
    - Resolve location references ("那里" → last mentioned location)
    - Maintain conversation state
    """
    
    # Pronouns and their types
    PRONOUNS = {
        "它": "any",  # Generic pronoun
        "他": "person",
        "她": "person",
        "这个": "any",
        "那个": "any",
        "那里": "location",
        "这里": "location",
    }
    
    # Entity type keywords for extraction
    ENTITY_KEYWORDS = {
        "stock": ["股价", "股票", "公司"],
        "location": ["天气", "气温", "城市"],
        "device": ["灯", "空调", "窗帘", "设备"],
        "music": ["歌", "音乐", "歌曲"],
    }
    
    def __init__(self, max_history: int = 10):
        """
        Initialize context resolver.
        
        Args:
            max_history: Maximum number of entities to track
        """
        self.entities: List[Entity] = []
        self.max_history = max_history
        self.conversation_state = {
            "last_topic": None,
            "last_intent": None,
        }
        
        logger.info(f"🧩 ContextResolver initialized (max_history={max_history})")
    
    def resolve(self, text: str) -> str:
        """
        Resolve references in text.
        
        Args:
            text: User query text
            
        Returns:
            Resolved text with pronouns replaced
        """
        resolved = text
        
        # Check for pronouns
        for pronoun, entity_type in self.PRONOUNS.items():
            if pronoun in text:
                # Find last mentioned entity of this type
                entity = self.get_last_entity(entity_type)
                if entity:
                    resolved = resolved.replace(pronoun, entity.value)
                    logger.info(f"🔄 Resolved '{pronoun}' → '{entity.value}' in: {text}")
        
        return resolved
    
    def extract_entities(self, text: str) -> List[Entity]:
        """
        Extract entities from text.
        
        Args:
            text: User query text
            
        Returns:
            List of extracted entities
        """
        entities = []
        
        # Simple keyword-based extraction
        # TODO: Use NER model for better extraction
        
        # Extract stock names (common patterns)
        stock_patterns = ["特斯拉", "苹果", "谷歌", "微软", "亚马逊", "阿里巴巴", "腾讯"]
        for stock in stock_patterns:
            if stock in text:
                entities.append(Entity(
                    type="stock",
                    value=stock,
                    context=text
                ))
        
        # Extract locations (common cities)
        location_patterns = ["北京", "上海", "深圳", "广州", "杭州", "成都", "重庆"]
        for location in location_patterns:
            if location in text:
                entities.append(Entity(
                    type="location",
                    value=location,
                    context=text
                ))
        
        # Extract devices (smart home)
        device_patterns = ["客厅的灯", "卧室的灯", "空调", "窗帘", "灯"]
        for device in device_patterns:
            if device in text:
                entities.append(Entity(
                    type="device",
                    value=device,
                    context=text
                ))
        
        return entities
    
    def update_context(self, text: str, intent: Optional[str] = None):
        """
        Update context with new query.
        
        Args:
            text: User query text
            intent: Detected intent (optional)
        """
        # Extract entities
        new_entities = self.extract_entities(text)
        
        # Add to history
        for entity in new_entities:
            self.entities.append(entity)
            logger.debug(f"  Added entity: {entity.type}={entity.value}")
        
        # Trim history
        if len(self.entities) > self.max_history:
            self.entities = self.entities[-self.max_history:]
        
        # Update conversation state
        if intent:
            self.conversation_state["last_intent"] = intent
        
        logger.debug(f"📝 Context updated: {len(self.entities)} entities tracked")
    
    def get_last_entity(self, entity_type: str = "any") -> Optional[Entity]:
        """
        Get the last mentioned entity of a specific type.
        
        Args:
            entity_type: Type of entity to retrieve ("any" for any type)
            
        Returns:
            Last mentioned entity or None
        """
        # Reverse search (most recent first)
        for entity in reversed(self.entities):
            if entity_type == "any" or entity.type == entity_type:
                return entity
        
        return None
    
    def get_entities_by_type(self, entity_type: str) -> List[Entity]:
        """Get all entities of a specific type."""
        return [e for e in self.entities if e.type == entity_type]
    
    def clear(self):
        """Clear all context."""
        self.entities.clear()
        self.conversation_state = {
            "last_topic": None,
            "last_intent": None,
        }
        logger.info("🗑️ Context cleared")


# Singleton instance
_context_resolver: Optional[ContextResolver] = None


def get_context_resolver() -> ContextResolver:
    """Get the global context resolver instance."""
    global _context_resolver
    
    if _context_resolver is None:
        _context_resolver = ContextResolver()
    
    return _context_resolver


# Quick test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    resolver = ContextResolver()
    
    print("\n" + "="*60)
    print("Context Resolver Test")
    print("="*60 + "\n")
    
    # Test conversation flow
    queries = [
        "特斯拉股价",
        "它涨了吗",
        "北京天气怎么样",
        "那里会下雨吗",
        "打开客厅的灯",
        "关闭它",
    ]
    
    for query in queries:
        print(f"User: {query}")
        
        # Resolve references
        resolved = resolver.resolve(query)
        if resolved != query:
            print(f"  → Resolved: {resolved}")
        
        # Update context
        resolver.update_context(query)
        
        # Show tracked entities
        if resolver.entities:
            print(f"  Tracked: {[(e.type, e.value) for e in resolver.entities[-3:]]}")
        
        print()
