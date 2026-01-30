"""
Comment Cache System
Pre-generates diverse comments using LLM and caches them for fast retrieval.
"""
import asyncio
import random
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta

class CommentCache:
    """
    Hybrid comment system:
    1. Uses cached comments for instant response
    2. Background LLM generates new comments to keep cache fresh
    """
    
    CACHE_FILE = Path(__file__).parent.parent / "data" / "comment_cache.json"
    MIN_CACHE_SIZE = 10  # Minimum comments per category
    
    # Default fallback comments (used when cache is empty)
    DEFAULT_COMMENTS = {
        "stock_up_big": [
            "哇，涨势喜人！",
            "今天表现强劲！",
            "真是势如破竹！",
            "涨得不错！",
            "看来多头占了上风。",
        ],
        "stock_down_big": [
            "哎呀，跌得有点狠...",
            "今天有点绿油油的...",
            "跌得不轻啊...",
            "空头占了先机。",
            "今天不太美丽...",
        ],
        "stock_stable": [
            "看起来今天波动不大，比较平稳。",
            "今天表现平平，没什么大波动。",
            "风平浪静的一天。",
            "价格比较稳定。",
            "今天没什么动静。",
        ],
        "stock_normal": [
            "市场总是有起有落嘛。",
            "来看看最新行情。",
            "帮您查到了。",
            "数据已经更新。",
            "这是最新的价格。",
            "实时数据来了。",
        ],
        "weather_good": [
            "今天天气不错！",
            "适合出门的好天气。",
            "天公作美啊。",
        ],
        "weather_bad": [
            "今天天气不太好...",
            "出门记得带伞。",
            "天气有点糟糕。",
        ],
        "news_intro": [
            "没问题，为您精选了几条最新新闻：",
            "来看看今天的新闻头条：",
            "以下是最新动态：",
            "新闻来了：",
        ],
    }
    
    def __init__(self):
        self.cache: Dict[str, List[str]] = {}
        self._load_cache()
        self._generating = False
        
    def _load_cache(self):
        """Load cache from file, fallback to defaults"""
        try:
            if self.CACHE_FILE.exists():
                with open(self.CACHE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.cache = data.get("comments", {})
                    # Merge with defaults
                    for key, defaults in self.DEFAULT_COMMENTS.items():
                        if key not in self.cache:
                            self.cache[key] = defaults
        except Exception:
            self.cache = dict(self.DEFAULT_COMMENTS)
    
    def _save_cache(self):
        """Save cache to file"""
        try:
            self.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(self.CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    "comments": self.cache,
                    "updated_at": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def get_comment(self, category: str) -> str:
        """Get a random comment from cache"""
        comments = self.cache.get(category, self.DEFAULT_COMMENTS.get(category, ["好的。"]))
        return random.choice(comments)
    
    def add_comment(self, category: str, comment: str):
        """Add a new comment to cache"""
        if category not in self.cache:
            self.cache[category] = []
        if comment not in self.cache[category]:
            self.cache[category].append(comment)
            # Keep cache size reasonable
            if len(self.cache[category]) > 50:
                self.cache[category] = self.cache[category][-50:]
            self._save_cache()
    
    async def generate_comments_async(self, llm_client=None):
        """
        Background task to generate new comments using LLM.
        Call this periodically or on startup.
        """
        if self._generating or llm_client is None:
            return
            
        self._generating = True
        try:
            prompts = {
                "stock_up_big": "生成5个表达股票大涨喜悦的短句，要自然口语化，每句不超过15字，用换行分隔",
                "stock_down_big": "生成5个表达股票大跌惋惜的短句，要自然口语化，每句不超过15字，用换行分隔",
                "stock_stable": "生成5个描述股票平稳无波动的短句，要自然口语化，每句不超过15字，用换行分隔",
                "stock_normal": "生成5个报告股票行情的开场白，要自然口语化，每句不超过15字，用换行分隔",
            }
            
            for category, prompt in prompts.items():
                try:
                    # This assumes llm_client has a chat method
                    response = await llm_client.chat(prompt)
                    if response:
                        new_comments = [c.strip() for c in response.split('\n') if c.strip() and len(c.strip()) < 20]
                        for comment in new_comments:
                            self.add_comment(category, comment)
                except Exception:
                    pass
                    
        finally:
            self._generating = False


# Global instance
_cache = None

def get_cache() -> CommentCache:
    global _cache
    if _cache is None:
        _cache = CommentCache()
    return _cache

def get_stock_comment(change_percent: float) -> str:
    """Get appropriate stock comment based on price change"""
    cache = get_cache()
    if change_percent > 5:
        return cache.get_comment("stock_up_big")
    elif change_percent < -5:
        return cache.get_comment("stock_down_big")
    elif abs(change_percent) < 0.5:
        return cache.get_comment("stock_stable")
    else:
        return cache.get_comment("stock_normal")

def get_news_comment() -> str:
    """Get news introduction comment"""
    return get_cache().get_comment("news_intro")
