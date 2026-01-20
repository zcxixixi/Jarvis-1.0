import feedparser
import yfinance as yf
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Executor for blocking I/O
_executor = ThreadPoolExecutor(max_workers=3)

async def get_news_briefing(source="combined"):
    """
    Fetch top news headlines from RSS feeds.
    Returns a string summary suitable for TTS.
    """
    feeds = {
        "bbc": "http://feeds.bbci.co.uk/news/world/rss.xml",
        # "xinhua": "http://www.xinhuanet.com/politics/news_politics.xml", # Often unstable
        "finance": "https://finance.yahoo.com/news/rssindex"
    }
    
    selected_feeds = [feeds["bbc"], feeds["finance"]]
    
    def fetch_rss():
        headlines = []
        for url in selected_feeds:
            try:
                feed = feedparser.parse(url)
                # Get top 2 entries from each
                for entry in feed.entries[:2]:
                    headlines.append(entry.title)
            except Exception as e:
                print(f"Error fetching RSS {url}: {e}")
        return headlines

    loop = asyncio.get_running_loop()
    try:
        headlines = await loop.run_in_executor(_executor, fetch_rss)
        if not headlines:
            return "抱歉，我暂时无法获取最新新闻。"
            
        # Format for speech
        response = "这是今天的热点新闻：\n"
        for i, title in enumerate(headlines, 1):
            response += f"{i}. {title}。\n"
        return response
    except Exception as e:
        return f"新闻获取失败：{str(e)}"

async def get_stock_price(query):
    """
    Get real-time price for a stock or crypto.
    Query examples: "AAPL", "Bitcoin", "Tesla", "茅台"
    """
    # Simple mapping for common Chinese names
    mappings = {
        "比特币": "BTC-USD",
        "以太坊": "ETH-USD",
        "茅台": "600519.SS",
        "腾讯": "0700.HK",
        "阿里": "BABA",
        "苹果": "AAPL",
        "特斯拉": "TSLA",
        "英伟达": "NVDA",
        "微软": "MSFT"
    }
    
    symbol = query
    # Check mapping
    for key, val in mappings.items():
        if key in query:
            symbol = val
            break
            
    # Default to US if not suffix (naive check)
    if not any(c in symbol for c in [".", "-"]) and not symbol.isupper():
        # Try to guess or just let yfinance handle it? 
        # yfinance usually needs exact ticker.
        pass

    def fetch_price(sym):
        try:
            ticker = yf.Ticker(sym)
            # fast_info is faster than .info
            price = ticker.fast_info.last_price
            # Change percentage
            prev_close = ticker.fast_info.previous_close
            change = ((price - prev_close) / prev_close) * 100
            
            currency = ticker.fast_info.currency
            return price, change, currency
        except Exception as e:
            print(f"Stock error: {e}")
            return None, None, None

    loop = asyncio.get_running_loop()
    try:
        price, change, currency = await loop.run_in_executor(_executor, fetch_price, symbol)
        
        if price is None:
            return f"抱歉，我没有找到 {symbol} 的行情数据。"
            
        direction = "涨" if change >= 0 else "跌"
        return f"{symbol} 当前价格为 {price:.2f} {currency}，今日{direction}幅 {abs(change):.2f}%。"
            
    except Exception as e:
        return f"查询失败: {str(e)}"

# Self-test
if __name__ == "__main__":
    async def test():
        print(await get_news_briefing())
        print(await get_stock_price("Bitcoin"))
        print(await get_stock_price("茅台"))
        
    asyncio.run(test())
