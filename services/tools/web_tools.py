"""
Web Tools
Provides web search and URL fetching functionality
"""
import aiohttp
import asyncio
import os
import re
from urllib.parse import quote
from typing import Dict, Any
from .base import BaseTool


class WebSearchTool(BaseTool):
    """Search the web using DuckDuckGo (no API key needed)"""
    
    @property
    def name(self) -> str:
        return "web_search"
    
    @property
    def description(self) -> str:
        return "搜索网络信息，获取最新内容"
    
    def get_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索关键词"
                        },
                        "num_results": {
                            "type": "integer",
                            "description": "返回结果数量（1-5）",
                            "default": 3
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    
    async def execute(self, **kwargs) -> str:
        """Search using DuckDuckGo instant answer API"""
        query = kwargs.get("query")
        num_results = kwargs.get("num_results", 3)
        if not query:
            return "❌ 错误：未提供搜索词"

        brave_key = os.getenv("BRAVE_SEARCH_API_KEY")
        try:
            async with aiohttp.ClientSession() as session:
                if brave_key:
                    url = f"https://api.search.brave.com/res/v1/web/search?q={quote(query)}&count={num_results}"
                    headers = {"Accept": "application/json", "X-Subscription-Token": brave_key}
                    async with session.get(url, headers=headers, timeout=10) as response:
                        if response.status != 200:
                            return f"实时搜索失败，状态码：{response.status}"

                        data = await response.json()
                        results = []
                        web = data.get("web", {}).get("results", [])
                        for item in web[:num_results]:
                            title = (item.get("title") or "").strip()
                            desc = (item.get("description") or "").strip()
                            link = (item.get("url") or "").strip()
                            line = " • ".join(part for part in [title, desc, link] if part)
                            if line:
                                results.append(f"• {line}")

                        if results:
                            return f"🔍 实时搜索结果 \"{query}\":\n\n" + "\n".join(results)
                        return f"🔍 未找到关于 \"{query}\" 的结果"

                # DuckDuckGo instant answer API (fallback)
                url = f"https://api.duckduckgo.com/?q={quote(query)}&format=json&no_html=1"
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()

                        results = []

                        # Abstract (main answer)
                        if data.get("Abstract"):
                            results.append(f"📝 {data['Abstract']}")
                            if data.get("AbstractSource"):
                                results.append(f"   来源: {data['AbstractSource']}")

                        # Related topics
                        topics = data.get("RelatedTopics", [])[:num_results]
                        for topic in topics:
                            if isinstance(topic, dict) and topic.get("Text"):
                                text = topic["Text"][:200]
                                results.append(f"• {text}")

                        if results:
                            return f"🔍 搜索结果 \"{query}\":\n\n" + "\n".join(results)
                        return f"🔍 未找到关于 \"{query}\" 的直接结果，建议在浏览器中搜索"
                    return f"搜索失败，状态码：{response.status}"
                        
        except asyncio.TimeoutError:
            return "抱歉，搜索服务响应超时，请稍后再试。"
        except Exception:
            return "抱歉，我现在连不上搜索服务，请稍后再试。"


class FetchUrlTool(BaseTool):
    """Fetch content from a URL"""
    
    @property
    def name(self) -> str:
        return "fetch_url"
    
    @property
    def description(self) -> str:
        return "获取网页内容（纯文本摘要）"
    
    def get_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "要获取的网页URL"
                        }
                    },
                    "required": ["url"]
                }
            }
        }
    
    async def execute(self, **kwargs) -> str:
        """Fetch and extract text from URL"""
        url = kwargs.get("url")
        if not url:
            return "❌ 错误：未提供 URL"
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; JarvisBot/1.0)"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        html = await response.text()
                        
                        # Simple text extraction
                        # Remove script and style elements
                        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
                        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
                        
                        # Remove HTML tags
                        text = re.sub(r'<[^>]+>', ' ', html)
                        
                        # Clean up whitespace
                        text = re.sub(r'\s+', ' ', text).strip()
                        
                        # Truncate to reasonable length
                        if len(text) > 1000:
                            text = text[:1000] + "..."
                        
                        return f"📄 网页内容摘要：\n{text}"
                    else:
                        return f"无法获取网页，状态码：{response.status}"
                        
        except asyncio.TimeoutError:
            return "抱歉，网页响应超时，请稍后再试。"
        except Exception:
            return "抱歉，我现在连不上该网页或网络不稳定，请稍后再试。"


class TranslateTool(BaseTool):
    """Translate text between languages"""
    
    @property
    def name(self) -> str:
        return "translate"
    
    @property
    def description(self) -> str:
        return "翻译文本（中英互译）"
    
    def get_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "要翻译的文本"
                        },
                        "to_lang": {
                            "type": "string",
                            "description": "目标语言：zh(中文), en(英文)",
                            "enum": ["zh", "en"]
                        }
                    },
                    "required": ["text", "to_lang"]
                }
            }
        }
    
    async def execute(self, **kwargs) -> str:
        """Translate using MyMemory API (free, no key needed)"""
        text = kwargs.get("text")
        to_lang = kwargs.get("to_lang", "en")
        if not text:
            return "❌ 错误：未提供翻译文本"
        try:
            # Detect source language (simple heuristic)
            has_chinese = any('\u4e00' <= c <= '\u9fff' for c in text)
            from_lang = "zh" if has_chinese else "en"
            
            if from_lang == to_lang:
                to_lang = "en" if from_lang == "zh" else "zh"
            
            lang_pair = f"{from_lang}|{to_lang}"
            
            url = f"https://api.mymemory.translated.net/get?q={quote(text)}&langpair={lang_pair}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        translation = data.get("responseData", {}).get("translatedText", "")
                        
                        if translation:
                            return f"🌐 翻译结果：\n{text}\n→ {translation}"
                        else:
                            return "翻译失败，请稍后重试"
                    else:
                        return f"翻译服务响应错误：{response.status}"
                        
        except asyncio.TimeoutError:
            return "抱歉，翻译服务响应超时，请稍后再试。"
        except Exception:
            return "抱歉，翻译服务暂时不可用，请稍后再试。"
