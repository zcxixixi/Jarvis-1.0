
import re
from typing import Dict, Any, Optional, Tuple

class IntentMatcher:
    """
    Handles regex-based intent extraction from user text.
    """
    
    @staticmethod
    def match_stock(text: str) -> Optional[str]:
        # 1) 优先匹配具体的股票/商品名称（具体优先于通用）
        cn_names = [
            # 具体公司/商品名
            "黄金", "白银",  # 贵金属
            "英伟达", "英伟", "特斯拉", "特斯", "苹果", "微软", "阿里", "腾讯", "茅台",
            "比特币", "比特", "以太坊", "以太", "百度", "京东", "拼多多", "美团", "小米",
            "亚马逊", "谷歌", "脸书",
        ]
        for name in cn_names:
            if name in text:
                return name

        # 2) Ticker/English names (whitelist)
        ticker_whitelist = {
            "nvda", "nvidia", "tsla", "tesla", "aapl", "apple", "msft", "microsoft",
            "baba", "alibaba", "tencent", "0700", "qqq", "spy", "btc", "eth", "amzn",
            "amazon", "meta", "goog", "googl", "google", "gold", "silver"
        }
        tokens = re.findall(r'\b[a-zA-Z0-9]{2,6}(?:-[a-zA-Z]{1,3})?\b', text)
        for tok in tokens:
            if tok.lower() in ticker_whitelist:
                return tok.upper()

        # 3) 最后才用通用关键词匹配（兜底，但只有在没找到具体名称时）
        if re.search(r'(股价|币价|行情|走势|股票)', text):
            # 检测到通用股票意图，但没有找到具体名称
            # 返回 None 让云端LLM处理
            return None

        return None

    @staticmethod
    def match_news(text: str) -> bool:
        return bool(re.search(r'(新闻|头条|热点|发生了什么)', text))

    @staticmethod
    def match_weather(text: str) -> Optional[str]:
        # Improved city extraction with comprehensive stopwords
        stopwords = [
            "天气", "查询", "的", "今天", "怎么样", "现在", "目前", 
            "帮我", "看看", "查一下", "情况", "怎样", "如何", "查查",
            "明天", "后天", "昨天", "预报", "告诉我", "问一下", "问问",
            "啊", "呢", "吧", "吗", "呀", "哦", "嗯", "那个",
            "你觉得", "有没有", "能不能", "请问", "我想知道", "搜一下",
            "告诉我", "给我也", "的一个", "点一首", "请听", "麻烦", "告诉",
            "外面", "冷不冷", "热不热", "多少度", "几度", "温度", "气温", "湿度",
            "下雨", "下雪", "刮风", "风大", "会不会", "要不要", "带伞"
        ]
        
        # Step 1: Remove all stopwords
        city = text
        for w in stopwords:
            city = city.replace(w, "")
        city = city.strip()
        
        # Step 2: If noisy content detected, clear and fallback to city matching
        noise_tokens = ["冷", "热", "下雨", "下雪", "刮风", "风", "外面", "今天", "现在", "明天", "后天", "多少度", "几度", "温度", "气温", "湿度", "雨", "雪"]
        if any(tok in city for tok in noise_tokens):
            city = ""

        # Step 3: If still too long or empty, try known city patterns
        if len(city) > 10 or not city:
            city_match = re.search(r'(北京|上海|广州|深圳|青岛|杭州|成都|重庆|武汉|西安|南京|苏州|天津|长沙|郑州|厦门|合肥|济南|福州|昆明|大连|宁波|无锡|东莞|佛山|沈阳|哈尔滨|深圳)', text)
            if city_match:
                city = city_match.group(1)
            else:
                city = "Beijing"  # Ultimate fallback
        
        # Step 3: Clean up any remaining noise (Only keep Chinese/English)
        city = re.sub(r'[^\u4e00-\u9fa5a-zA-Z]', '', city)
        if not city:
            city = "Beijing"
            
        return city

    @staticmethod
    def match_music(text: str) -> Tuple[Optional[str], Optional[str]]:
        """Returns (action, query)"""
        # Stop
        if any(kw in text for kw in ["停止", "暂停", "关掉", "结束"]):
            return "stop", None
        
        # List
        if "列表" in text:
            return "list", None
            
        # Play
        stopwords = ["播放", "来首", "音乐", "放一首", "听", "我要", "给我", "的", "歌", "播", "放", "为您", "好的", "一首", "点一个", "点一首", "请听"]
        query = text
        
        # Extract content from brackets if present (e.g. 《彩虹》)
        bracketed = re.search(r"《(.+?)》", text)
        if bracketed:
            query = bracketed.group(1)
        else:
            for w in stopwords:
                query = query.replace(w, "")
        
        query = query.strip()
        
        # Random/Generic
        if not query or query in ["随便", "好听", "背景", "复习"] or len(query) < 1:
            return "play_random", None
            
        return "play_specific", query

    @staticmethod
    def match_web_search(text: str) -> str:
        stopwords = ["搜索", "查询", "查找", "帮我", "一下", "请", "给我", "帮忙"]
        query = text
        for w in stopwords:
            query = query.replace(w, "")
        return query.strip() or text.strip()

    @staticmethod
    def match_light_control(text: str) -> str:
        if "开" in text: return "on"
        if "关" in text: return "off"
        return "status"
