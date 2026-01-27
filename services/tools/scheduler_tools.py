"""
Scheduler Tools
Exposes scheduler capabilities to the Agent
"""

from typing import Dict, Any, Optional
from jarvis_assistant.services.tools.base import BaseTool
from jarvis_assistant.core.scheduler import get_scheduler


class ScheduleReminderTool(BaseTool):
    @property
    def name(self) -> str:
        return "schedule_reminder"
    
    @property
    def description(self) -> str:
        return "在稍后或定期安排提醒或任务"
    
    def get_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "要做的任务描述"
                        },
                        "delay_seconds": {
                            "type": "integer",
                            "description": "触发前的等待秒数 (默认 0)"
                        },
                        "interval_seconds": {
                            "type": "integer",
                            "description": "循环间隔秒数 (0 表示单次提醒)"
                        }
                    },
                    "required": ["description"]
                }
            }
        }
    
    async def execute(self, **kwargs) -> str:
        description = kwargs.get("description")
        delay_seconds = kwargs.get("delay_seconds", 0)
        interval_seconds = kwargs.get("interval_seconds", 0)
        
        scheduler = get_scheduler()
        
        # Default to 1 hour if no time specified and it looks like a reminder
        if delay_seconds == 0 and interval_seconds == 0:
             delay_seconds = 3600
        
        task_id = scheduler.add_task(description, interval_seconds, delay_seconds)
        
        if interval_seconds > 0:
            return f"✅ 已为您设置循环任务：'{description}'，每隔 {interval_seconds} 秒执行一次。(ID: {task_id})"
        else:
            return f"✅ 已为您设置提醒：'{description}'，将在 {delay_seconds} 秒后执行。(ID: {task_id})"

class ListRemindersTool(BaseTool):
    @property
    def name(self) -> str:
        return "list_reminders"
    
    @property
    def description(self) -> str:
        return "列出当前所有已安排的提醒和任务"
    
    def get_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    
    async def execute(self, **kwargs) -> str:
        scheduler = get_scheduler()
        tasks = scheduler.tasks
        
        if not tasks:
            return "目前没有任何待办提醒。"
        
        lines = ["📅 您的日程提醒清单："]
        for t in tasks.values():
            import time
            due_in = int(t.next_run - time.time())
            lines.append(f"- [{t.task_id}] {t.description} (将在 {due_in} 秒后触发)")
            
        return "\n".join(lines)

class CancelReminderTool(BaseTool):
    @property
    def name(self) -> str:
        return "cancel_reminder"
    
    @property
    def description(self) -> str:
        return "取消已安排的提醒"
    
    def get_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "要取消的任务ID"
                        }
                    },
                    "required": ["task_id"]
                }
            }
        }
    
    async def execute(self, **kwargs) -> str:
        task_id = kwargs.get("task_id")
        scheduler = get_scheduler()
        if scheduler.remove_task(task_id):
            return f"✅ 好的，已成功取消 ID 为 {task_id} 的提醒。"
        else:
            return f"❌ 抱歉，我没找到 ID 为 {task_id} 的提醒。"
