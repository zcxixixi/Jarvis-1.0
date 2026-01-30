"""
Semantic Memory Enhancement
Adds semantic search capability to memory store
"""

import json
from typing import List, Dict, Any
from datetime import datetime
import re


class SemanticMemory:
    """Enhanced memory with semantic search and pattern recognition"""
    
    def __init__(self, memory_store):
        self.memory = memory_store
    
    def semantic_search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search conversations using semantic similarity
        
        Currently uses keyword matching with smart scoring.
        Future: Can be upgraded to use embeddings for true semantic search.
        """
        query_lower = query.lower()
        query_words = set(re.findall(r'\w+', query_lower))
        
        scored_convs = []
        for conv in self.memory.conversations:
            content = conv.get('content', '').lower()
            
            # Score based on word overlap
            content_words = set(re.findall(r'\w+', content))
            overlap = len(query_words & content_words)
            
            # Bonus for exact phrase match
            if query_lower in content:
                overlap += 5
            
            if overlap > 0:
                scored_convs.append((overlap, conv))
        
        # Sort by score descending
        scored_convs.sort(reverse=True, key=lambda x: x[0])
        
        return [conv for score, conv in scored_convs[:limit]]
    
    def find_patterns(self) -> Dict[str, Any]:
        """
        Recognize patterns in user behavior
        
        Returns:
            Dictionary of detected patterns
        """
        patterns = {
            "common_topics": {},
            "frequent_tools": {},
            "time_patterns": {},
            "user_preferences": {}
        }
        
        # Analyze conversations
        for conv in self.memory.conversations:
            content = conv.get('content', '')
            role = conv.get('role', '')
            
            # Count tool usage from assistant responses
            if role == 'assistant':
                # Simple tool detection
                if '天气' in content:
                    patterns["common_topics"]["weather"] = patterns["common_topics"].get("weather", 0) + 1
                if '时间' in content or '几点' in content:
                    patterns["common_topics"]["time"] = patterns["common_topics"].get("time", 0) + 1
                if '计算' in content:
                    patterns["common_topics"]["calculator"] = patterns["common_topics"].get("calculator", 0) + 1
        
        # Analyze task history for tool usage
        for task in self.memory.task_history:
            for step in task.get('steps', []):
                if step:
                    patterns["frequent_tools"][step] = patterns["frequent_tools"].get(step, 0) + 1
        
        return patterns
    
    def auto_summarize(self, conversation_ids: List[int] = None, max_length: int = 200) -> str:
        """
        Auto-summarize conversations
        
        Args:
            conversation_ids: Specific conversations to summarize (None = recent)
            max_length: Max summary length
        
        Returns:
            Summary text
        """
        if conversation_ids is None:
            # Summarize recent conversations
            convs = self.memory.get_context(limit=20)
        else:
            convs = [self.memory.conversations[i] for i in conversation_ids 
                    if i < len(self.memory.conversations)]
        
        if not convs:
            return "No conversations to summarize."
        
        # Extract key information
        user_queries = []
        assistant_responses = []
        
        for conv in convs:
            role = conv.get('role')
            content = conv.get('content', '')
            
            if role == 'user':
                user_queries.append(content)
            elif role == 'assistant':
                # Extract first sentence or first 50 chars
                first_part = content.split('\n')[0][:50]
                assistant_responses.append(first_part)
        
        # Build summary
        summary_parts = []
        
        if user_queries:
            # List main topics
            topics = set()
            for q in user_queries:
                if '天气' in q:
                    topics.add('weather')
                if '时间' in q or '几点' in q:
                    topics.add('time')
                if '计算' in q:
                    topics.add('calculation')
            
            if topics:
                summary_parts.append(f"Topics discussed: {', '.join(topics)}")
        
        summary_parts.append(f"Total interactions: {len(convs)}")
        summary_parts.append(f"User queries: {len(user_queries)}")
        
        summary = ". ".join(summary_parts)
        
        if len(summary) > max_length:
            summary = summary[:max_length-3] + "..."
        
        return summary
    
    def get_user_context(self) -> str:
        """Get a context summary for the agent to understand the user better"""
        patterns = self.find_patterns()
        summary = self.auto_summarize()
        
        context = f"""User Context:
- Recent activity: {summary}
- Common topics: {', '.join(patterns['common_topics'].keys())}
- Frequent tools: {', '.join(list(patterns['frequent_tools'].keys())[:3])}
"""
        return context


# Integration helper
def enhance_memory(memory_store):
    """Add semantic capabilities to existing memory store"""
    return SemanticMemory(memory_store)


# Quick test
if __name__ == "__main__":
    from jarvis_assistant.core.memory import get_memory
    
    mem = get_memory()
    semantic = SemanticMemory(mem)
    
    print("🔍 Testing semantic search...")
    results = semantic.semantic_search("天气")
    print(f"  Found {len(results)} weather-related conversations")
    
    print("\n📊 Finding patterns...")
    patterns = semantic.find_patterns()
    print(f"  Common topics: {patterns['common_topics']}")
    
    print("\n📝 Auto-summary...")
    summary = semantic.auto_summarize()
    print(f"  {summary}")
    
    print("\n✅ Semantic memory working!")
