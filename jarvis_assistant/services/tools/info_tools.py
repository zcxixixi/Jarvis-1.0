"""
Information Tools for Jarvis
News briefing and stock price monitoring.
"""
from typing import Dict, Any, List, Optional, Union
import re
import feedparser
import yfinance as yf
import asyncio
from concurrent.futures import ThreadPoolExecutor
from .base import BaseTool
from jarvis_assistant.utils.validators import DataAuthenticityValidator

# Executor for blocking I/O
_executor = ThreadPoolExecutor(max_workers=3)

class NewsBriefingTool(BaseTool):
    def __init__(self):
        self.validator = DataAuthenticityValidator()

    @property
    def name(self) -> str:
        return "get_news"
    
    @property
    def description(self) -> str:
        return "获取最新新闻简报(Reuters RSS)"
    
    def get_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "description": "新闻类别 (world, finance)", "default": "world"}
                    }
                }
            }
        }
    
    async def execute(self, **kwargs) -> str:
        feeds = {
            # 中文新闻源优先
            "world": [
                "https://rss.sina.com.cn/news/world.xml",  # 新浪国际新闻
                "https://news.163.com/special/00011K6L/rss_newstop.xml",  # 网易头条
                "https://feeds.bbci.co.uk/zhongwen/simp/rss.xml",  # BBC中文
            ],
            "finance": [
                "https://rss.sina.com.cn/finance.xml",  # 新浪财经
                "https://finance.163.com/special/00251LR5/finance_rss.xml",  # 网易财经
                "https://feeds.reuters.com/reuters/businessNews",  # 路透社
            ],
            "tech": [
                "https://rss.sina.com.cn/tech.xml",  # 新浪科技
                "https://news.163.com/special/00011K6L/rss_tech.xml",  # 网易科技
            ],
        }
        
        category = kwargs.get("category", "world")
        sources = feeds.get(category, feeds["world"])
        
        def fetch_rss(url):
            try:
                feed = feedparser.parse(url)
                headlines = [entry.title for entry in feed.entries[:3]]
                return headlines
            except Exception:
                return []

        loop = asyncio.get_running_loop()
        try:
            for url in sources:
                # Validate source authenticity
                if not self.validator.validate_source("news", url):
                    continue
                headlines = await loop.run_in_executor(_executor, fetch_rss, url)
                if headlines:
                    from urllib.parse import urlparse
                    source = urlparse(url).netloc
                    response = f"没问题，为您精选了几条最新的{category}新闻（来自 {source}）：\n"
                    for i, title in enumerate(headlines, 1):
                        response += f"{i}. {title}。\n"
                    response += "\n您对哪条感兴趣吗？"
                    return response
            return "抱歉，我暂时无法连接到新闻服务器，请稍后再试。"
        except Exception:
            return "抱歉，获取新闻时遇到了点麻烦，我会尽快修复。"

class StockPriceTool(BaseTool):
    def __init__(self):
        self.validator = DataAuthenticityValidator()

    @property
    def name(self) -> str:
        return "get_stock_price"
    
    @property
    def description(self) -> str:
        return "获取股票/加密货币实时价格(Yahoo Finance)"
    
    def get_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "description": "股票代码或名称 (如: AAPL, 比特币, 茅台)"}
                    },
                    "required": ["symbol"]
                }
            }
        }
    
    async def execute(self, **kwargs) -> str:
        query = kwargs.get("symbol")
        if not query:
            return "请告诉我您想查询的股票名称或代码。"
            
        # yfinance fetches real market data from Yahoo Finance
        if not self.validator.validate_source("web", "finance.yahoo.com"):
            return "抱歉，无法访问行情服务器。"

        # 股票名称映射 (中文名 -> (代码, 显示名))
        mappings = {
            # Crypto
            "比特": ("BTC-USD", "比特币"), "比特币": ("BTC-USD", "比特币"), "btc": ("BTC-USD", "比特币"),
            "以太": ("ETH-USD", "以太坊"), "以太坊": ("ETH-USD", "以太坊"), "eth": ("ETH-USD", "以太坊"),
            # 贵金属
            "黄金": ("GC=F", "黄金"), "gold": ("GC=F", "黄金"),
            "白银": ("SI=F", "白银"), "silver": ("SI=F", "白银"),
            # China stocks
            "茅台": ("600519.SS", "贵州茅台"), "贵州茅台": ("600519.SS", "贵州茅台"),
            # US/HK stocks (CN/EN aliases)
            "腾讯": ("0700.HK", "腾讯"), "tencent": ("0700.HK", "腾讯"),
            "阿里": ("BABA", "阿里巴巴"), "阿里巴巴": ("BABA", "阿里巴巴"), "alibaba": ("BABA", "阿里巴巴"),
            "苹果": ("AAPL", "苹果"), "apple": ("AAPL", "苹果"),
            "特斯": ("TSLA", "特斯拉"), "特斯拉": ("TSLA", "特斯拉"), "tesla": ("TSLA", "特斯拉"),
            "英伟": ("NVDA", "英伟达"), "英伟达": ("NVDA", "英伟达"), "nvidia": ("NVDA", "英伟达"), "nvda": ("NVDA", "英伟达"),
            "微软": ("MSFT", "微软"), "microsoft": ("MSFT", "微软"),
            "亚马逊": ("AMZN", "亚马逊"), "amazon": ("AMZN", "亚马逊"),
            "谷歌": ("GOOG", "谷歌"), "google": ("GOOG", "谷歌"),
            "meta": ("META", "Meta"), "脸书": ("META", "Meta"),
            "百度": ("BIDU", "百度"), "京东": ("JD", "京东"), "拼多多": ("PDD", "拼多多"),
            "美团": ("3690.HK", "美团"), "小米": ("1810.HK", "小米"),
        }
        
        symbol = query.strip()
        display_name = query.strip()  # 默认用原始查询作为显示名
        ql = symbol.lower()
        for key, val in mappings.items():
            if key in ql:
                symbol = val[0]
                display_name = val[1]  # 使用预定义的股票名
                break

        # Normalize ticker case for pure alpha tickers
        if re.fullmatch(r'[A-Za-z]{1,6}(?:-[A-Za-z]{1,3})?', symbol):
            symbol = symbol.upper()

        def fetch_price(sym):
            try:
                ticker = yf.Ticker(sym)
                fast = ticker.fast_info
                price = fast.last_price
                if price is None or price == 0:
                    return None, None, None
                prev_close = fast.previous_close
                if prev_close is None or prev_close == 0:
                    return None, None, None
                change = ((price - prev_close) / prev_close) * 100
                currency = fast.currency
                return price, change, currency
            except Exception:
                return None, None, None

        loop = asyncio.get_running_loop()
        try:
            price, change, currency = await loop.run_in_executor(_executor, fetch_price, symbol)
            if price is None:
                return f"抱歉，我没有找到 {display_name} 的实时行情数据，请确认代码是否正确。"
                
            if change is None:
                return f"我查到了，{display_name}（{symbol}）目前的报价是 {price:.2f} {currency}。"
            
            direction = "上涨" if change >= 0 else "下跌"
            # Use cached comments for diversity
            from jarvis_assistant.utils.comment_cache import get_stock_comment
            comment = get_stock_comment(change)
                
            return f"{comment} {display_name}（{symbol}）现价 {price:.2f} {currency}，今日{direction}了 {abs(change):.2f}%。"
        except Exception as e:
            return "查询行情时出了一点小状况，请稍后再试。"


# -------------------------------
# Backward-compatible helpers used by hybrid_jarvis.py
# -------------------------------
async def get_news_briefing(category: str = "world") -> str:
    """Fetch latest news briefing (compat wrapper)."""
    tool = NewsBriefingTool()
    return await tool.execute(category=category)


async def get_stock_price(symbol: str) -> str:
    """Fetch stock/crypto price (compat wrapper)."""
    tool = StockPriceTool()
    return await tool.execute(symbol=symbol)
