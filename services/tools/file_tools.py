"""
File Tools
Standard file operations for Jarvis
"""
import os
import glob
from typing import Dict, Any, List
from .base import BaseTool

class FileReadTool(BaseTool):
    @property
    def name(self) -> str: return "read_file"
    @property
    def description(self) -> str: return "读取文件内容"
    def get_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "文件路径"}
                    },
                    "required": ["path"]
                }
            }
        }
    async def execute(self, **kwargs) -> str:
        path = kwargs.get("path")
        if not path: return "❌ 未指定路径"
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"❌ 读取失败: {e}"

class FileWriteTool(BaseTool):
    @property
    def name(self) -> str: return "write_file"
    @property
    def description(self) -> str: return "写入文件内容"
    def get_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "文件路径"},
                        "content": {"type": "string", "description": "写入内容"}
                    },
                    "required": ["path", "content"]
                }
            }
        }
    async def execute(self, **kwargs) -> str:
        path = kwargs.get("path")
        content = kwargs.get("content")
        if not path: return "❌ 未指定路径"
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"✅ 写入成功: {path}"
        except Exception as e:
            return f"❌ 写入失败: {e}"

class ListDirTool(BaseTool):
    @property
    def name(self) -> str: return "list_dir"
    @property
    def description(self) -> str: return "列出目录内容"
    def get_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "目录路径", "default": "."}
                    }
                }
            }
        }
    async def execute(self, **kwargs) -> str:
        path = kwargs.get("path", ".")
        try:
            items = os.listdir(path)
            return "\n".join(items) if items else "目录为空"
        except Exception as e:
            return f"❌ 列出目录失败: {e}"
