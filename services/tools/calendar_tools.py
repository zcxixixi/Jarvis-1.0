"""
Calendar Tools for Jarvis
Allows scheduling and viewing events using local persistent storage.
"""
from typing import Dict, Any, List
import json
import os
from pathlib import Path
from .base import BaseTool
from jarvis_assistant.utils.validators import DataAuthenticityValidator

# Local storage path
CALENDAR_FILE = Path.home() / ".jarvis_calendar.json"

def load_calendar():
    if not CALENDAR_FILE.exists():
        return []
    try:
        with open(CALENDAR_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_calendar(events):
    with open(CALENDAR_FILE, 'w', encoding='utf-8') as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

class AddCalendarEventTool(BaseTool):
    def __init__(self):
        self.validator = DataAuthenticityValidator()

    @property
    def name(self) -> str:
        return "add_calendar_event"
    
    @property
    def description(self) -> str:
        return "记录日程到本地日历(本地存储)"
    
    def get_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "event": {"type": "string", "description": "日程内容描述"},
                        "time": {"type": "string", "description": "时间 (例如: '明天下午3点')"}
                    },
                    "required": ["event", "time"]
                }
            }
        }
    
    async def execute(self, **kwargs) -> str:
        event = kwargs.get("event")
        time_str = kwargs.get("time")
        
        if not event or not time_str:
            return "抱歉，我需要明确的事件内容和时间才能帮您记录日程。"
            
        events = load_calendar()
        new_event = {
            "event": event,
            "time": time_str,
            "created_at": str(os.times()) # Simple timestamp
        }
        events.append(new_event)
        save_calendar(events)
        
        return f"好的，已经为您记录在案：\n📅 事件：{event}\n⏰ 时间：{time_str}"

class ListCalendarEventsTool(BaseTool):
    def __init__(self):
        self.validator = DataAuthenticityValidator()

    @property
    def name(self) -> str:
        return "list_calendar_events"
    
    @property
    def description(self) -> str:
        return "查看本地日历中的日程(本地存储)"
    
    def get_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "关键词过滤 (可选)"}
                    }
                }
            }
        }
    
    async def execute(self, **kwargs) -> str:
        query = kwargs.get("query", "").lower()
        events = load_calendar()
        
        if not events:
            return "您的日历目前是空的，需要我为您安排点什么吗？"
            
        filtered = events
        if query:
            filtered = [e for e in events if query in e["event"].lower() or query in e["time"].lower()]
            
        if not filtered:
            return f"没有找到与 '{query}' 相关的日程。"
            
        result = "这是为您找到的日程安排：\n"
        for item in filtered[-10:]: # Show last 10
            result += f"- {item['time']}: {item['event']}\n"
            
        return result
