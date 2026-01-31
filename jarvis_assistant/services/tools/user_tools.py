"""
User Profile Tools
Tools for updating and retrieving persistent user information (location, name, etc.)
"""
from typing import Dict, Any
from .base import BaseTool
from jarvis_assistant.core.memory import get_memory

class UpdateUserInfoTool(BaseTool):
    """Update user profile information"""
    
    @property
    def name(self) -> str:
        return "update_user_info"
    
    @property
    def description(self) -> str:
        return "更新用户画像信息，如位置、姓名、偏好等"
    
    def get_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "信息类别，如: location, name, dietary_preference, hobby",
                            "enum": ["location", "name", "dietary_preference", "hobby", "other"]
                        },
                        "value": {
                            "type": "string",
                            "description": "具体内容，如: Heze, Kai, Vegetarian"
                        }
                    },
                    "required": ["key", "value"]
                }
            }
        }
    
    async def execute(self, **kwargs) -> str:
        key = kwargs.get("key")
        value = kwargs.get("value")
        
        memory = get_memory()
        memory.set_profile(key, value)
        
        return f"✅ 已更新用户{key}: {value}"

class GetUserInfoTool(BaseTool):
    """Get user profile information"""
    
    @property
    def name(self) -> str:
        return "get_user_info"
    
    @property
    def description(self) -> str:
        return "获取用户画像信息"
    
    def get_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "信息类别，如果不确定的可以留空获取所有"
                        }
                    }
                }
            }
        }
    
    async def execute(self, **kwargs) -> str:
        key = kwargs.get("key")
        memory = get_memory()
        
        if key:
            val = memory.get_profile(key)
            if val:
                return f"{key}: {val}"
            else:
                return f"未知 {key}"
        else:
            profile = memory.get_all_profile()
            return f"用户画像: {profile}"


class ViewMyProfileTool(BaseTool):
    """View all information Jarvis remembers about the user"""
    
    @property
    def name(self) -> str:
        return "view_my_profile"
    
    @property
    def description(self) -> str:
        return "查看 Jarvis 记住的所有用户信息"
    
    def get_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        }
    
    async def execute(self, **kwargs) -> str:
        memory = get_memory()
        profile = memory.get_all_profile()
        
        # Format nicely
        lines = ["📋 **Jarvis 记住的关于你的信息**:\n"]
        
        # Basics
        basics = profile.get("basics", {})
        if basics:
            lines.append("**基本信息**:")
            for k, v in basics.items():
                lines.append(f"  • {k}: {v}")
            lines.append("")
        
        # Current Focus
        focus = profile.get("current_focus", {})
        if focus:
            lines.append("**当前关注**:")
            for k, v in focus.items():
                if k != "last_updated":
                    lines.append(f"  • {k}: {v}")
            lines.append("")
        
        # Interests
        interests = profile.get("interests", {})
        if interests:
            lines.append("**兴趣偏好**:")
            for k, v in interests.items():
                lines.append(f"  • {k}: {v}")
            lines.append("")
        
        # Recent Topics
        topics = profile.get("recent_topics", [])
        if topics:
            lines.append("**最近讨论的话题**:")
            for t in topics[:3]:  # Show only top 3
                lines.append(f"  • {t.get('topic')} ({t.get('date')})")
        
        if len(lines) == 1:
            return "我还没有记住关于你的信息。"
        
        return "\n".join(lines)


class ForgetInfoTool(BaseTool):
    """Forget specific user information"""
    
    @property
    def name(self) -> str:
        return "forget_info"
    
    @property
    def description(self) -> str:
        return "删除特定的用户信息（如项目、学习方向等）"
    
    def get_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "类别: basics, current_focus, interests, all",
                            "enum": ["basics", "current_focus", "interests", "all"]
                        },
                        "key": {
                            "type": "string",
                            "description": "具体项（如果删除整个类别可留空）"
                        }
                    },
                    "required": ["category"]
                }
            }
        }
    
    async def execute(self, **kwargs) -> str:
        category = kwargs.get("category")
        key = kwargs.get("key")
        
        memory = get_memory()
        profile = memory.get_all_profile()
        
        if category == "all":
            memory.user_profile = {
                "basics": {},
                "current_focus": {},
                "interests": {},
                "recent_topics": []
            }
            memory.save()
            return "✅ 已清空所有记忆"
        
        if category in profile:
            if key:
                # Delete specific key
                if isinstance(profile[category], dict) and key in profile[category]:
                    del profile[category][key]
                    memory.save()
                    return f"✅ 已删除 {category}.{key}"
                else:
                    return f"未找到 {category}.{key}"
            else:
                # Delete entire category
                if category == "recent_topics":
                    profile[category] = []
                else:
                    profile[category] = {}
                memory.save()
                return f"✅ 已清空 {category}"
        
        return f"未知类别: {category}"

