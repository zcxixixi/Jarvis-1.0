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
    
    def __init__(self):
        self.classification_cache = {}  # 缓存分类结果
        logger.info(f"IntentClassifier initialized - Unified Architecture Mode")
    
    def classify(self, text: str) -> str:
        """
        分类查询意图
        
        Args:
            text: 用户查询文本
            
        Returns:
            "complex" - 始终走 Unified Agent
        """
        # Phase 7 Refactor: All traffic is complex/agent routed.
        # Simple patterns removed.
        return "complex"
    
    def clear_cache(self):
        """清空缓存"""
        self.classification_cache.clear()
