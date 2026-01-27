"""
Feedback Manager for Jarvis
Handles user feedback, learning, and preference adaptation.
"""

import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

class FeedbackManager:
    """
    Manages user feedback and learns from it.
    Stores:
    1. Negative feedback (mistakes to avoid)
    2. Explicit preferences (favored tools/params)
    """
    
    def __init__(self, storage_path: str = "~/.jarvis/feedback.json"):
        self.path = Path(storage_path).expanduser()
        self.data = {
            "negative_feedback": [], # [{query, tool, reason, timestamp}]
            "preferences": {},       # {category: tool_name} e.g., {'music': 'netease'}
            "tool_success_rate": {}  # {tool_name: {success: int, fail: int}}
        }
        self.load()
        
    def load(self):
        """Load feedback data"""
        if self.path.exists():
            try:
                with open(self.path, 'r') as f:
                    self.data = json.load(f)
            except Exception as e:
                print(f"⚠️ Feedback load error: {e}")
                
    def save(self):
        """Save feedback data"""
        try:
            with open(self.path, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"❌ Feedback save error: {e}")

    def record_feedback(self, last_task: str, last_tool: str, feedback_type: str, user_comment: str = ""):
        """
        Record user feedback for a task
        feedback_type: 'positive' or 'negative'
        """
        timestamp = datetime.now().isoformat()
        
        if feedback_type == 'negative':
            # Record mistake
            entry = {
                "task": last_task,
                "tool": last_tool,
                "user_comment": user_comment,
                "timestamp": timestamp
            }
            self.data["negative_feedback"].append(entry)
            
            # Update tool stats
            if last_tool:
                if last_tool not in self.data["tool_success_rate"]:
                    self.data["tool_success_rate"][last_tool] = {"success": 0, "fail": 0}
                self.data["tool_success_rate"][last_tool]["fail"] += 1
                
            print(f"📝 Learned from mistake: Don't use {last_tool} for '{last_task}'")
            
        elif feedback_type == 'positive':
            # Update tool stats
            if last_tool:
                if last_tool not in self.data["tool_success_rate"]:
                    self.data["tool_success_rate"][last_tool] = {"success": 0, "fail": 0}
                self.data["tool_success_rate"][last_tool]["success"] += 1
                
        self.save()

    def set_preference(self, category: str, tool_name: str):
        """Set a explicit preference"""
        self.data["preferences"][category] = tool_name
        self.save()
        print(f"📝 Preference set: Use {tool_name} for {category}")

    def get_advice(self, current_task: str) -> List[str]:
        """
        Get advice/warnings based on past feedback
        Returns list of warnings (e.g. "Avoid tool X")
        """
        advice = []
        
        # Check negative feedback for similar tasks
        # Simple keyword matching for now
        for entry in self.data["negative_feedback"]:
            # Check overlap
            task_words = set(current_task.lower().split())
            history_words = set(entry["task"].lower().split())
            overlap = len(task_words & history_words)
            
            if overlap >= 2: # Significant overlap
                advice.append(f"Avoid {entry['tool']} (User complained: {entry.get('user_comment', 'fail')})")
                
        return advice

    def get_preferred_tool(self, category: str) -> Optional[str]:
        """Get preferred tool for a category"""
        return self.data["preferences"].get(category)


# Singleton
_feedback_instance = None

def get_feedback_manager() -> FeedbackManager:
    global _feedback_instance
    if _feedback_instance is None:
        _feedback_instance = FeedbackManager()
    return _feedback_instance
