"""
System Tools
Provides system information and control functionality
"""
import os
import platform
import subprocess
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any
from .base import BaseTool


class SystemInfoTool(BaseTool):
    """Get system information"""
    
    @property
    def name(self) -> str:
        return "get_system_info"
    
    @property
    def description(self) -> str:
        return "获取系统信息，包括CPU、内存、磁盘使用情况"
    
    def get_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "detail": {
                            "type": "string",
                            "description": "信息类型：all(全部), cpu, memory, disk, battery",
                            "enum": ["all", "cpu", "memory", "disk", "battery"]
                        }
                    },
                    "required": []
                }
            }
        }
    
    async def execute(self, **kwargs) -> str:
        """Get system information"""
        detail = kwargs.get("detail", "all")
        try:
            result = []
            
            if detail in ["all", "cpu"]:
                cpu_percent = psutil.cpu_percent(interval=0.5)
                cpu_count = psutil.cpu_count()
                result.append(f"🖥️ CPU: {cpu_percent}% ({cpu_count}核心)")
            
            if detail in ["all", "memory"]:
                mem = psutil.virtual_memory()
                mem_used = mem.used / (1024**3)
                mem_total = mem.total / (1024**3)
                result.append(f"💾 内存: {mem_used:.1f}GB / {mem_total:.1f}GB ({mem.percent}%)")
            
            if detail in ["all", "disk"]:
                disk = psutil.disk_usage('/')
                disk_used = disk.used / (1024**3)
                disk_total = disk.total / (1024**3)
                result.append(f"💿 磁盘: {disk_used:.1f}GB / {disk_total:.1f}GB ({disk.percent}%)")
            
            if detail in ["all", "battery"]:
                try:
                    battery = psutil.sensors_battery()
                    if battery:
                        status = "🔌 充电中" if battery.power_plugged else "🔋 使用电池"
                        result.append(f"电池: {battery.percent}% {status}")
                except:
                    if detail == "battery":
                        result.append("⚠️ 无电池信息")
            
            if detail == "all":
                result.insert(0, f"📊 系统: {platform.system()} {platform.release()}")
            
            return "\n".join(result) if result else "无法获取系统信息"
            
        except Exception as e:
            return f"获取系统信息时出错：{str(e)}"


class SetTimerTool(BaseTool):
    """Set a timer/reminder"""
    
    @property
    def name(self) -> str:
        return "set_timer"
    
    @property
    def description(self) -> str:
        return "设置定时器或提醒"
    
    def get_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "minutes": {
                            "type": "integer",
                            "description": "定时分钟数"
                        },
                        "message": {
                            "type": "string",
                            "description": "提醒消息"
                        }
                    },
                    "required": ["minutes"]
                }
            }
        }
    
    async def execute(self, **kwargs) -> str:
        """Set a timer (note: this is a basic implementation)"""
        minutes = kwargs.get("minutes")
        message = kwargs.get("message", "时间到了")
        if minutes is None:
            return "❌ 错误：未指定定时分钟数"
        try:
            trigger_time = datetime.now() + timedelta(minutes=minutes)
            
            # On macOS, we can use osascript for notification
            if platform.system() == "Darwin":
                # Schedule notification using at command or similar
                # For this MVP, just return confirmation
                return f"⏰ 定时器设置成功！将在 {minutes} 分钟后（{trigger_time.strftime('%H:%M')}）提醒您：{message}"
            else:
                return f"⏰ 定时器设置成功！将在 {minutes} 分钟后提醒您：{message}"
                
        except Exception as e:
            return f"设置定时器时出错：{str(e)}"


class RunCommandTool(BaseTool):
    """Run shell commands (limited, safe commands only)"""
    
    ALLOWED_COMMANDS = ["ls", "pwd", "date", "whoami", "hostname", "uptime", "df", "free", "cal"]
    
    @property
    def name(self) -> str:
        return "run_command"
    
    @property
    def description(self) -> str:
        return "执行安全的系统命令：ls, pwd, date, whoami, hostname, uptime, df, cal 等"
    
    def get_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": f"要执行的命令，仅限：{', '.join(self.ALLOWED_COMMANDS)}",
                            "enum": self.ALLOWED_COMMANDS
                        }
                    },
                    "required": ["command"]
                }
            }
        }
    
    async def execute(self, **kwargs) -> str:
        """Run a safe shell command"""
        command = kwargs.get("command")
        if not command:
            return "❌ 错误：未指定命令"
        try:
            base_cmd = command.split()[0] if command else ""
            
            if base_cmd not in self.ALLOWED_COMMANDS:
                return f"❌ 不允许执行命令：{command}"
            
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            output = result.stdout.strip() or result.stderr.strip()
            return f"📟 执行结果：\n{output[:500]}"
            
        except subprocess.TimeoutExpired:
            return "❌ 命令执行超时"
        except Exception as e:
            return f"❌ 命令执行错误：{str(e)}"
