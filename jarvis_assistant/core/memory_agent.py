"""
Memory Agent - Active Information Extraction
Automatically identifies and saves important user information from conversations
"""
import re
import json
from typing import Optional, Dict, Any
from jarvis_assistant.core.memory import get_memory


class MemoryAgent:
    """
    主动记忆提取器
    分析对话内容，智能识别并保存用户的重要信息
    """
    
    def __init__(self):
        self.memory = get_memory()
        
        # Pattern definitions
        self.project_patterns = [
            r"我(?:最近|现在)?(?:在|正在)写(.+?)论文",
            r"我的论文(?:是|关于)(.+)",
            r"我(?:最近|现在)?(?:在|正在)研究(.+)",
            r"我的项目(?:是|关于)(.+)"
        ]
        
        self.learning_patterns = [
            r"我(?:想|要|在)学(?:习)?(.+)",
            r"我正在学(.+)"
        ]
        
        self.interest_patterns = [
            r"我喜欢(.+)",
            r"我爱好是(.+)"
        ]
    
    async def analyze_and_extract(self, user_input: str, assistant_response: str = "") -> None:
        """
        分析对话，提取重要信息
        
        Args:
            user_input: 用户输入
            assistant_response: Jarvis 回复（可选，用于话题识别）
        """
        
        # 1. Extract Project/Research
        await self._extract_project(user_input)
        
        # 2. Extract Learning Focus
        await self._extract_learning(user_input)
        
        # 3. Extract Interests
        await self._extract_interests(user_input)
        
        # 4. Identify and record topic
        await self._record_topic(user_input, assistant_response)
    
    async def _extract_project(self, text: str) -> None:
        """提取项目/研究方向"""
        for pattern in self.project_patterns:
            match = re.search(pattern, text)
            if match:
                project = match.group(1).strip()
                
                # If there's more detail after "关于", include it
                if "关于" in text:
                    detail_match = re.search(r"关于(.+?)(?:[，。]|$)", text)
                    if detail_match:
                        detail = detail_match.group(1).strip()
                        project = f"{project}论文 - {detail}"
                    else:
                        project = f"{project}论文"
                else:
                    # Clean up common prefixes
                    project = project.replace("一篇", "").replace("关于", "").replace("是", "").strip()
                    if "论文" not in project:
                        project = f"{project}论文"
                
                # Save
                self.memory.set_current_focus("project", project, auto=True)
                
                # Try to extract research area (before "论文")
                if "论文" in project:
                    area_match = re.search(r"(.+?)论文", project)
                    if area_match:
                        area = area_match.group(1).strip()
                        if len(area) > 1:
                            self.memory.set_current_focus("research_area", area, auto=True)
                break
    
    async def _extract_learning(self, text: str) -> None:
        """提取学习方向"""
        for pattern in self.learning_patterns:
            match = re.search(pattern, text)
            if match:
                learning = match.group(1).strip()
                # Clean up common suffixes
                learning = learning.replace("一下", "").strip()
                
                if len(learning) > 1:  # Avoid single chars
                    self.memory.set_current_focus("learning", learning, auto=True)
                break
    
    async def _extract_interests(self, text: str) -> None:
        """提取兴趣爱好"""
        for pattern in self.interest_patterns:
            match = re.search(pattern, text)
            if match:
                interest = match.group(1).strip()
                
                # Categorize by keyword
                if any(k in interest for k in ["喝", "咖啡", "茶"]):
                    self.memory.set_interest("beverage", interest)
                elif any(k in interest for k in ["音乐", "歌", "听"]):
                    self.memory.set_interest("music", interest)
                else:
                    self.memory.set_interest("general", interest)
                break
    
    async def _record_topic(self, user_input: str, assistant_response: str) -> None:
        """
        识别并记录讨论的话题
        只记录技术/学术相关的话题，忽略天气、音乐等工具查询
        """
        # Skip if it's a simple tool query
        if any(kw in user_input for kw in ["天气", "股价", "音乐", "时间", "计算"]):
            return
        
        # Identify technical topics from keywords
        tech_keywords = {
            "深度学习", "机器学习", "强化学习", "神经网络",
            "控制理论", "PID", "算法", "数据结构",
            "Python", "编程", "代码", "优化"
        }
        
        for keyword in tech_keywords:
            if keyword in user_input or keyword in assistant_response:
                self.memory.add_recent_topic(keyword)
                return
        
        # If response is long and technical (>100 chars), try to extract topic
        if len(assistant_response) > 100:
            # Use simple heuristic: look for capitalized terms or quoted terms
            # This is a placeholder - in production, use LLM extraction
            pass


# Singleton instance
_memory_agent_instance: Optional[MemoryAgent] = None


def get_memory_agent() -> MemoryAgent:
    """Get the global memory agent instance"""
    global _memory_agent_instance
    if _memory_agent_instance is None:
        _memory_agent_instance = MemoryAgent()
    return _memory_agent_instance
