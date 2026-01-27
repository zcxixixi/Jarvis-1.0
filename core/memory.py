"""
Jarvis Memory Store
Persistent storage for conversation history, task logs, and user preferences.
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path


class MemoryStore:
    """Persistent memory for Jarvis Agent"""
    
    def __init__(self, path: str = "~/.jarvis/memory.json"):
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        
        # Core memory structures
        self.conversations: List[Dict[str, Any]] = []
        self.task_history: List[Dict[str, Any]] = []
        self.preferences: Dict[str, Any] = {}
        self.session_id: str = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Load existing memory
        self.load()
    
    def load(self) -> None:
        """Load memory from disk"""
        if self.path.exists():
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.conversations = data.get('conversations', [])
                    self.task_history = data.get('task_history', [])
                    self.preferences = data.get('preferences', {})
                print(f"📚 Memory loaded: {len(self.conversations)} conversations, {len(self.task_history)} tasks")
            except Exception as e:
                print(f"⚠️ Failed to load memory: {e}")
    
    def save(self) -> None:
        """Save memory to disk"""
        try:
            data = {
                'last_updated': datetime.now().isoformat(),
                'conversations': self.conversations[-1000:],  # Keep last 1000
                'task_history': self.task_history[-500:],      # Keep last 500
                'preferences': self.preferences,
            }
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to save memory: {e}")
    
    def add_conversation(self, role: str, content: str, metadata: Optional[Dict] = None) -> None:
        """Add a conversation turn"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'session_id': self.session_id,
            'role': role,  # 'user', 'assistant', 'system'
            'content': content,
        }
        if metadata:
            entry['metadata'] = metadata
        self.conversations.append(entry)
        self.save()
    
    def add_task(self, task: str, steps: List[str], result: str, success: bool) -> None:
        """Log a completed task"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'session_id': self.session_id,
            'task': task,
            'steps': steps,
            'result': result,
            'success': success,
        }
        self.task_history.append(entry)
        self.save()
    
    def get_context(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation context"""
        return self.conversations[-limit:]
    
    def get_context_string(self, limit: int = 10) -> str:
        """Get context as formatted string for LLM"""
        context = self.get_context(limit)
        lines = []
        for entry in context:
            role = entry['role'].upper()
            content = entry['content']
            lines.append(f"[{role}]: {content}")
        return "\n".join(lines)
    
    def search_history(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search conversation history"""
        results = []
        for entry in reversed(self.conversations):
            if query.lower() in entry['content'].lower():
                results.append(entry)
                if len(results) >= limit:
                    break
        return results
    
    def set_preference(self, key: str, value: Any) -> None:
        """Set a user preference"""
        self.preferences[key] = value
        self.save()
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference"""
        return self.preferences.get(key, default)
    
    def clear_session(self) -> None:
        """Clear current session conversations"""
        self.conversations = [c for c in self.conversations if c.get('session_id') != self.session_id]
        self.save()


# Singleton instance
_memory_instance: Optional[MemoryStore] = None


def get_memory() -> MemoryStore:
    """Get the global memory store instance"""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = MemoryStore()
    return _memory_instance
