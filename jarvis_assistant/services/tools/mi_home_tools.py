"""
Mi Home Tools
Control Xiaomi Smart Home devices using python-miio
"""
import asyncio
from typing import Dict, Any, List
from .base import BaseTool

# Try to import python-miio, provide graceful fallback
try:
    from miio import Device, Yeelight, ChuangmiPlug, AirPurifier
    MIIO_AVAILABLE = True
except ImportError:
    MIIO_AVAILABLE = False


import json
import os
from pathlib import Path

# Load Device Config
MI_DEVICES = {}
_config_path = Path("xiaomi_devices.json")
if _config_path.exists():
    try:
        with open(_config_path, "r") as f:
            MI_DEVICES = json.load(f)
    except Exception as e:
        print(f"⚠️ Error loading xiaomi_devices.json: {e}")

# Also check .env for MI_DEVICES_JSON string
_env_devices = os.getenv("MI_DEVICES_JSON")
if _env_devices:
    try:
        MI_DEVICES.update(json.loads(_env_devices))
    except: pass


class MiDeviceScannerTool(BaseTool):
    """Scan for Xiaomi devices on local network"""
    
    @property
    def name(self) -> str:
        return "scan_xiaomi_devices"
    
    @property
    def description(self) -> str:
        return "扫描局域网内的小米智能设备"
    
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
        """Scan for devices"""
        if not MIIO_AVAILABLE:
            return "❌ python-miio 库未安装。请运行 `pip install python-miio`"
            
        try:
            # First try miiocli which is robust
            import subprocess
            process = await asyncio.create_subprocess_shell(
                "miiocli discover",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            output = stdout.decode().strip()
            
            # Also list known devices from config
            known = ""
            if MI_DEVICES:
                known = "\n\n📚 已配置设备 (Available for control):\n"
                for k, v in MI_DEVICES.items():
                    known += f"- {k} ({v.get('model')}) @ {v.get('ip')}\n"
            
            if not output:
                return f"🔍 扫描未发现新设备。{known}"
                
            return f"🔍 扫描结果：\n{output}{known}"
            
        except Exception as e:
            return f"❌ 扫描出错：{str(e)}"


class MiLightTool(BaseTool):
    """Control Xiaomi/Yeelight Smart Lights"""
    
    @property
    def name(self) -> str:
        return "control_xiaomi_light"
    
    @property
    def description(self) -> str:
        # Dynamic description based on config
        devices_str = ", ".join(MI_DEVICES.keys()) if MI_DEVICES else "需提供IP/Token"
        return f"控制小米智能灯。已知设备: {devices_str}"
    
    def get_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "device_name": {
                            "type": "string", 
                            "description": "设备名称 (配置中的 key, 例如 'bedroom_light')",
                            "enum": list(MI_DEVICES.keys()) if MI_DEVICES else []
                        },
                        "ip": {"type": "string", "description": "设备IP (如果未配置名称)"},
                        "token": {"type": "string", "description": "设备Token (如果未配置名称)"},
                        "action": {"type": "string", "enum": ["on", "off", "toggle", "brightness", "color"], "description": "操作"},
                        "value": {"type": "integer", "description": "亮度(1-100)"}
                    },
                    "required": ["action"] 
                }
            }
        }
    
    async def execute(self, **kwargs) -> str:
        if not MIIO_AVAILABLE:
            return "❌ python-miio 库未安装"
            
        device_name = kwargs.get("device_name")
        ip = kwargs.get("ip")
        token = kwargs.get("token")
        action = kwargs.get("action")
        value = kwargs.get("value")

        # Resolve device from config
        if device_name and device_name in MI_DEVICES:
            conf = MI_DEVICES[device_name]
            ip = conf.get("ip")
            token = conf.get("token")
            
        if not ip or not token or not action:
            return f"❌ 错误：缺少 IP/Token 或设备未配置 (Name: {device_name})"

        try:
            # Yeelight specific control
            light = Yeelight(ip=ip, token=token)
            
            if action == "on":
                light.on()
                return f"💡 {device_name or ip} 已打开"
            elif action == "off":
                light.off()
                return f"🌑 {device_name or ip} 已关闭"
            elif action == "toggle":
                light.toggle()
                return f"💡 {device_name or ip} 状态已切换"
            elif action == "brightness":
                if value:
                    light.set_brightness(value)
                    return f"🔆 {device_name or ip} 亮度设为 {value}%"
                return str(light.status())
            
            return f"❌ 未知操作：{action}"
        except Exception as e:
            return f"❌ 控制失败 ({device_name or ip}): {str(e)}"

# Note: More devices (Air Purifier, Vacuum, Fan) can be added similarly
