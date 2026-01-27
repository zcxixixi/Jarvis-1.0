"""
Jarvis Scheduler System
Enables proactive task execution based on time and events.
Strictly follows User Experience (no nagging) and Authenticity (real time only) principles.
"""

import asyncio
import time
import json
import uuid
from datetime import datetime
from typing import List, Dict, Callable, Any, Optional
from pathlib import Path


class ScheduledTask:
    def __init__(self, task_id: str, description: str, interval: int = 0, next_run: float = 0, task_type: str = "interval"):
        self.task_id = task_id
        self.description = description  # Natural language description
        self.interval = interval        # In seconds
        self.next_run = next_run        # Unix timestamp
        self.task_type = task_type      # 'interval', 'one_off', 'cron'
        self.enabled = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "interval": self.interval,
            "next_run": self.next_run,
            "task_type": self.task_type,
            "enabled": self.enabled
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScheduledTask':
        task = cls(
            task_id=data["task_id"],
            description=data["description"],
            interval=data["interval"],
            next_run=data["next_run"],
            task_type=data.get("task_type", "interval")
        )
        task.enabled = data.get("enabled", True)
        return task


class Scheduler:
    """
    Manages background tasks and proactive notifications.
    Persists tasks to disk to survive restarts.
    """
    
    def __init__(self, memory_path: str = "~/.jarvis/scheduler.json"):
        self.path = Path(memory_path).expanduser()
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self.agent_callback = None  # Function to call to execute agent action
        
        # Load existing tasks
        self.load()
        
    def load(self):
        """Load scheduled tasks from disk"""
        if self.path.exists():
            try:
                with open(self.path, 'r') as f:
                    data = json.load(f)
                    for task_data in data.get("tasks", []):
                        task = ScheduledTask.from_dict(task_data)
                        # Don't run stale one-off tasks immediately if they expired long ago
                        if task.task_type == "one_off" and task.next_run < time.time() - 300:
                            print(f"⚠️ Scheduler: Skipping stale task '{task.description}'")
                            continue
                        self.tasks[task.task_id] = task
                print(f"⏰ Scheduler loaded {len(self.tasks)} tasks")
            except Exception as e:
                print(f"❌ Scheduler load error: {e}")

    def save(self):
        """Save tasks to disk"""
        try:
            data = {"tasks": [t.to_dict() for t in self.tasks.values()]}
            with open(self.path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"❌ Scheduler save error: {e}")

    def add_task(self, description: str, interval_seconds: int, delay_seconds: int = 0) -> str:
        """
        Add a new proactive task.
        
        Args:
            description: What to do (e.g., "Check weather", "Stretch posture")
            interval_seconds: Repeat interval (0 for one-off)
            delay_seconds: How many seconds from now to start
        """
        task_id = str(uuid.uuid4())[:8]
        next_run = time.time() + delay_seconds
        
        task = ScheduledTask(
            task_id=task_id,
            description=description,
            interval=interval_seconds,
            next_run=next_run,
            task_type="interval" if interval_seconds > 0 else "one_off"
        )
        
        self.tasks[task_id] = task
        self.save()
        print(f"⏰ Scheduled: '{description}' in {delay_seconds}s (ID: {task_id})")
        return task_id

    def remove_task(self, task_id: str) -> bool:
        """Cancel a task"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            self.save()
            return True
        return False

    def set_callback(self, callback: Callable[[str], Any]):
        """Set the function to call when a task triggers (usually Agent.run)"""
        self.agent_callback = callback

    async def start(self):
        """Start the scheduler loop"""
        self.running = True
        print("⏰ Scheduler started")
        
        while self.running:
            now = time.time()
            triggered_tasks = []
            
            # Check for due tasks
            for task_id, task in list(self.tasks.items()):
                if task.enabled and task.next_run <= now:
                    triggered_tasks.append(task)
            
            # Execute triggered tasks
            for task in triggered_tasks:
                print(f"⏰ Triggering task: {task.description}")
                
                # Update next run time BEFORE execution (to prevent double execution if it crashes)
                if task.task_type == "interval" and task.interval > 0:
                    task.next_run = now + task.interval
                else:
                    # One-off task complete
                    self.remove_task(task.task_id)
                self.save() # Persist update
                
                # Execute action via agent
                if self.agent_callback:
                    try:
                        # Notify user purely
                        # Authenticity check: Ensure we are only triggering based on real time
                        print(f"⏰ [Real-Time Event] Executing: {task.description}")
                        
                        # We run this as a background task
                        asyncio.create_task(self.agent_callback(f"System Trigger: {task.description}"))
                    except Exception as e:
                        print(f"❌ Task execution error: {e}")
            
            # Sleep to prevent high CPU usage
            await asyncio.sleep(1.0)

    def stop(self):
        self.running = False


# Singleton
_scheduler_instance = None

def get_scheduler() -> Scheduler:
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = Scheduler()
    return _scheduler_instance


# Quick Test
if __name__ == "__main__":
    async def mock_agent_run(prompt):
        print(f"🤖 Agent running: {prompt}")

    async def main():
        sched = get_scheduler()
        sched.set_callback(mock_agent_run)
        
        # Determine test file path
        sched.path = Path("/tmp/jarvis_test_scheduler.json")
        
        print("Adding one-off task (2s delay)...")
        sched.add_task("Say hello", 0, delay_seconds=2)
        
        print("Adding interval task (3s interval)...")
        sched.add_task("Check system status", 3, delay_seconds=1)
        
        # Run for 7 seconds
        task = asyncio.create_task(sched.start())
        await asyncio.sleep(7)
        sched.stop()
        await task

    asyncio.run(main())
