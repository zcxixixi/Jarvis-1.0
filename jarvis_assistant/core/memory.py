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
        self.user_profile: Dict[str, Any] = {}  # 🔥 Init profile
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
                    self.user_profile = data.get('user_profile', {})  # 🔥 Load profile
                
                # 🔥 Migrate to hierarchical structure if needed
                self._migrate_profile_if_needed()
                
                print(f"📚 Memory loaded: {len(self.conversations)} convs, {len(self.user_profile)} profile items")
            except Exception as e:
                print(f"⚠️ Failed to load memory: {e}")
    
    def save(self) -> None:
        """Save memory to disk"""
        try:
            data = {
                'last_updated': datetime.now().isoformat(),
                'conversations': self.conversations[-1000:],
                'task_history': self.task_history[-500:],
                'preferences': self.preferences,
                'user_profile': self.user_profile,  # 🔥 Save profile
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
        """Set a user preference (system config like volume, etc)"""
        self.preferences[key] = value
        self.save()
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        return self.preferences.get(key, default)

    # ============================================================
    # 🔥 Enhanced User Profile (Hierarchical Structure)
    # ============================================================
    
    def _migrate_profile_if_needed(self):
        """Migrate old flat profile to hierarchical structure"""
        if not isinstance(self.user_profile, dict):
            self.user_profile = {}
        
        # Check if already hierarchical
        if "basics" in self.user_profile or "current_focus" in self.user_profile:
            return  # Already migrated
        
        # Migrate flat structure
        old_profile = self.user_profile.copy()
        self.user_profile = {
            "basics": {},
            "current_focus": {},
            "interests": {},
            "recent_topics": []
        }
        
        # Move known keys
        for key in ["name", "location"]:
            if key in old_profile:
                self.user_profile["basics"][key] = old_profile.pop(key)
        
        # Move remaining to interests
        for key, val in old_profile.items():
            self.user_profile["interests"][key] = val
        
        self.save()
    
    def set_profile(self, key: str, value: Any) -> None:
        """Set a basic user profile fact (location, name, etc) - legacy compat"""
        print(f"📝 Updating Profile: {key} = {value}")
        self.user_profile.setdefault("basics", {})[key] = value
        self.save()
    
    def get_profile(self, key: str, default: Any = None) -> Any:
        """Get basic profile value - legacy compat"""
        return self.user_profile.get("basics", {}).get(key, default)
    
    def get_all_profile(self) -> Dict[str, Any]:
        return self.user_profile
    
    def set_current_focus(self, key: str, value: str, auto: bool = False) -> None:
        """
        Set user's current focus (project, learning, research_area)
        
        Args:
            key: Category (project, learning, research_area)
            value: Content
            auto: If True, was automatically extracted (not explicitly told)
        """
        from datetime import datetime
        
        if "current_focus" not in self.user_profile:
            self.user_profile["current_focus"] = {}
        
        # Check if this item already exists
        existing = self.user_profile["current_focus"].get(key)
        
        if isinstance(existing, dict) and "value" in existing:
            # Already structured with count - increment
            if existing["value"] == value:
                existing["count"] += 1
                existing["last_mentioned"] = datetime.now().isoformat()
                marker = "🤖 (自动识别)" if auto else "👤 (用户告知)"
                print(f"💡 再次提及: {key} = {value} (共{existing['count']}次) {marker}")
            else:
                # Different value - replace and reset count
                self.user_profile["current_focus"][key] = {
                    "value": value,
                    "count": 1,
                    "last_mentioned": datetime.now().isoformat()
                }
                marker = "🤖 (自动识别)" if auto else "👤 (用户告知)"
                print(f"💡 更新记忆: {key} = {value} {marker}")
        else:
            # First time or old format - create structured entry
            self.user_profile["current_focus"][key] = {
                "value": value,
                "count": 1,
                "last_mentioned": datetime.now().isoformat()
            }
            marker = "🤖 (自动识别)" if auto else "👤 (用户告知)"
            print(f"💡 记住了: {key} = {value} {marker}")
        
        self.save()
    
    def set_interest(self, key: str, value: str) -> None:
        """Set user interest/preference"""
        if "interests" not in self.user_profile:
            self.user_profile["interests"] = {}
        
        self.user_profile["interests"][key] = value
        print(f"❤️ 记住兴趣: {key} = {value}")
        self.save()
    
    def add_recent_topic(self, topic: str) -> None:
        """Add a recently discussed topic"""
        from datetime import datetime
        
        if "recent_topics" not in self.user_profile:
            self.user_profile["recent_topics"] = []
        
        # Avoid duplicates
        topics = self.user_profile["recent_topics"]
        if any(t.get("topic") == topic for t in topics):
            return
        
        topics.insert(0, {
            "topic": topic,
            "date": datetime.now().strftime("%Y-%m-%d")
        })
        
        # Keep only last 5 topics
        self.user_profile["recent_topics"] = topics[:5]
        self.save()
    
    def get_context_for_response(self) -> Dict[str, Any]:
        """
        Get user context suitable for injecting into LLM responses
        Returns a dict with relevant context pieces (including time-decayed weights)
        """
        from datetime import datetime
        
        context = {}
        
        # Current focus (now supports weighted entries with time decay)
        focus = self.user_profile.get("current_focus", {})
        if focus:
            for key in ["project", "learning", "research_area"]:
                if key in focus:
                    item = focus[key]
                    if isinstance(item, dict) and "value" in item:
                        # New structured format with decay
                        raw_count = item.get("count", 1)
                        last_mentioned = item.get("last_mentioned")
                        
                        # Calculate effective weight with time decay
                        effective_count = self._calculate_decayed_weight(raw_count, last_mentioned)
                        
                        # Only include if weight > 0.5 (threshold)
                        if effective_count >= 0.5:
                            context[key] = item["value"]
                            context[f"{key}_count"] = effective_count
                            context[f"{key}_raw_count"] = raw_count  # For debugging
                    else:
                        # Old format (plain string) - backward compatible
                        context[key] = item
                        context[f"{key}_count"] = 1
        
        # Basics
        basics = self.user_profile.get("basics", {})
        if "location" in basics:
            context["location"] = basics["location"]
        if "name" in basics:
            context["name"] = basics["name"]
        
        return context
    
    def _calculate_decayed_weight(self, raw_count: int, last_mentioned_str: str) -> float:
        """
        Calculate time-decayed weight using exponential decay
        
        Formula: effective_count = raw_count * exp(-λ * days_elapsed)
        
        Decay parameters:
        - Half-life: 14 days (2 weeks)
        - After 14 days: weight drops to 50%
        - After 28 days: weight drops to 25%
        - After 56 days: weight drops to 6.25%
        
        Args:
            raw_count: Original mention count
            last_mentioned_str: ISO timestamp of last mention
            
        Returns:
            Effective weight (float)
        """
        from datetime import datetime
        import math
        
        if not last_mentioned_str:
            # No timestamp - assume fresh
            return float(raw_count)
        
        try:
            last_mentioned = datetime.fromisoformat(last_mentioned_str)
            now = datetime.now()
            days_elapsed = (now - last_mentioned).total_seconds() / 86400  # Convert to days
            
            # Exponential decay with 14-day half-life
            # λ = ln(2) / half_life
            half_life_days = 14
            decay_constant = math.log(2) / half_life_days
            
            # Decay factor
            decay_factor = math.exp(-decay_constant * days_elapsed)
            
            # Effective weight
            effective = raw_count * decay_factor
            
            return max(0, effective)  # Never negative
            
        except Exception:
            # If parsing fails, return raw count
            return float(raw_count)
        return context

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
