"""
Intent Classifier - 意图分类器
快速判断查询是否需要深度处理（Agent + 工具）
"""
import logging

logger = logging.getLogger(__name__)


class IntentClassifier:
    """意图分类器 - 判断查询是简单对话还是需要工具调用"""
    
    # 工具关键词（需要 Agent 处理）
    TOOL_KEYWORDS = [
        # 金融
        "股价", "股票", "基金", "汇率", "黄金", "价格",
        # 信息查询
        "新闻", "搜索", "查询", "查找",
        # 通讯
        "邮件", "短信", "电话",
        # 日程
        "日程", "提醒", "闹钟", "定时",
        # 媒体
        "播放", "音乐", "歌", "视频",
        # 智能家居
        "打开", "关闭", "灯", "空调", "窗帘",
        # 分析
        "分析", "计算", "统计",
        # 天气 [FIX] Add weather keywords
        "天气", "天气预报", "气温", "下雨", "晴天",
        # 其他
        "帮我", "论文"
    ]
    
    # 简单问候/闲聊模式
    SIMPLE_PATTERNS = [
        "你好", "早上好", "晚上好", "晚安", "再见",
        "几点", "星期几", "谢谢", "不客气",
        "讲个笑话", "怎么样"  # [FIX] Removed "天气怎么样" - weather should use Agent
    ]
    
    def __init__(self):
        self.classification_cache = {}  # 缓存分类结果
        logger.info(f"IntentClassifier initialized with {len(self.TOOL_KEYWORDS)} tool keywords")
    
    def classify(self, text: str) -> str:
        """
        分类查询意图
        
        Args:
            text: 用户查询文本
            
        Returns:
            "simple" - 简单对话，走 S2S
            "complex" - 复杂查询，走 Agent
        """
        text = text.strip()
        
        # 检查缓存
        if text in self.classification_cache:
            return self.classification_cache[text]
        
        # 1. 检查工具关键词（优先级最高）
        matched_tools = [kw for kw in self.TOOL_KEYWORDS if kw in text]
        if matched_tools:
            logger.info(f"[CLASSIFIER] '{text}' -> COMPLEX (tools: {matched_tools})")
            self.classification_cache[text] = "complex"
            return "complex"
        
        # 2. 检查简单模式
        matched_simple = [p for p in self.SIMPLE_PATTERNS if p in text]
        if matched_simple:
            logger.info(f"[CLASSIFIER] '{text}' -> SIMPLE (patterns: {matched_simple})")
            self.classification_cache[text] = "simple"
            return "simple"
        
        # 3. 基于长度的默认策略
        if len(text) < 15:
            logger.info(f"[CLASSIFIER] '{text}' -> SIMPLE (short query, len={len(text)})")
            self.classification_cache[text] = "simple"
            return "simple"
        
        logger.info(f"[CLASSIFIER] '{text}' -> COMPLEX (default, len={len(text)})")
        self.classification_cache[text] = "complex"
        return "complex"
    
    def clear_cache(self):
        """清空缓存"""
        self.classification_cache.clear()
