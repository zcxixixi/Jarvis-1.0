"""
Jarvis Agent Core
Autonomous agent with planning, execution, and verification loop.
"""

import asyncio
import json
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from jarvis_assistant.core.memory import get_memory
from jarvis_assistant.core.intent_matcher import IntentMatcher
from jarvis_assistant.services.tools import get_all_tools


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class PlanStep:
    """A single step in an execution plan"""
    description: str
    tool_name: Optional[str] = None
    tool_args: Dict[str, Any] = field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    retry_count: int = 0


@dataclass
class ExecutionPlan:
    """Multi-step execution plan"""
    task: str
    steps: List[PlanStep] = field(default_factory=list)
    final_result: Optional[str] = None
    success: bool = False


class JarvisAgent:
    """
    Autonomous Jarvis Agent with:
    - Task planning and decomposition
    - Multi-step tool execution
    - Self-correction on failures
    - Persistent memory
    """
    
    MAX_RETRIES = 2
    
    def __init__(self):
        print("🤖 Initializing Jarvis Agent...")
        self.memory = get_memory()
        
        # Add semantic memory capabilities
        from jarvis_assistant.core.semantic_memory import enhance_memory
        self.semantic_memory = enhance_memory(self.memory)
        
        # Use plugin manager for dynamic tool loading
        from jarvis_assistant.utils import get_plugin_manager
        plugin_mgr = get_plugin_manager()
        self.tools = plugin_mgr.loaded_plugins

        # Add feedback manager (Phase 5)
        from jarvis_assistant.core.feedback_manager import get_feedback_manager # Wait, where is feedback_manager?
        self.feedback = get_feedback_manager()
        
        print(f"🔧 Loaded {len(self.tools)} tools via plugin manager")
        
        # Intent to tool mapping for quick routing
        self.intent_keywords = {
            "天气": "get_weather",
            "几点": "get_current_time",
            "时间": "get_current_time",
            "计算": "calculate",
            "播放": "play_music",
            "音乐": "play_music",
            "停止": "play_music",
            "开灯": "control_xiaomi_light",
            "关灯": "control_xiaomi_light",
            "读取文件": "read_file",
            "写入文件": "write_file",
            "查看目录": "list_dir",
            "发邮件": "send_email",
            "写邮件": "send_email",
            "查看邮件": "list_emails",
            "收件箱": "list_emails",
            "添加日程": "add_calendar_event",
            "安排日程": "add_calendar_event",
            "查看日程": "list_calendar_events",
            "日历": "list_calendar_events",
            "提醒": "schedule_reminder",
            # News & Stocks
            "新闻": "get_news",
            "头条": "get_news",
            "热点": "get_news",
            "股价": "get_stock_price",
            "币价": "get_stock_price",
            "行情": "get_stock_price",
            "走势": "get_stock_price",
            "价格": "get_stock_price",
            # Web search (explicit)
            "搜索": "web_search",
            # Feedback
            "不对": "feedback_negative", # New intent for feedback
            "错了": "feedback_negative",
            "不是": "feedback_negative",
            "很好": "feedback_positive",
        }
        
        # Initialize Scheduler
        from jarvis_assistant.core.scheduler import get_scheduler
        self.scheduler = get_scheduler()
        self.scheduler.set_callback(self.handle_trigger)
        
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.scheduler.start())
        except RuntimeError:
            pass 

    async def handle_trigger(self, prompt: str):
        # ... existing code ...
        print(f"⚡ Proactive Trigger: {prompt}")
        await self.run(prompt)
    
    async def run(self, user_input: str, stream_callback: Optional[callable] = None) -> str:
        """
        Main agent loop with Self-Learning
        """
        # 🎵 Auto-pause music when user speaks (to prevent overlap with Jarvis response)
        music_tool = self.tools.get("play_music")
        if music_tool and hasattr(music_tool, '_current_process') and music_tool._current_process:
            try:
                print("🔇 Pausing background music...")
                music_tool._current_process.terminate()
                music_tool._current_process = None
            except:
                pass
        
        # Check for feedback keywords first
        if user_input in ["不对", "错了", "不是这个", "wrong", "stop"]:
             return await self.handle_user_feedback("negative", user_input)
             
        # Store user input
        self.memory.add_conversation("user", user_input)
        
        try:
            # 1. Plan (with learning)
            plan = await self.plan(user_input)
            
            # Check advice from feedback manager
            advice = self.feedback.get_advice(user_input)
            if advice:
                print(f"🧠 Learning recall: {'; '.join(advice)}")
                # TODO: Re-plan if heavy warning? For now just log.
            
            print(f"📋 Plan created: {len(plan.steps)} steps")
            
            # ... execution loop ...
            for i, step in enumerate(plan.steps):
                print(f"🔄 Step {i+1}/{len(plan.steps)}: {step.description}")
                step.status = StepStatus.RUNNING
                
                result = await self.execute_step(step, stream_callback)
                
                if step.status == StepStatus.FAILED and step.retry_count < self.MAX_RETRIES:
                     # ... retry logic ...
                     print(f"⚠️ Step failed, retrying... ({step.retry_count + 1}/{self.MAX_RETRIES})")
                     step.retry_count += 1
                     step.status = StepStatus.RETRYING
                     result = await self.execute_step(step)
            
            # 3. Synthesize result
            final_result = self.synthesize(plan)
            plan.final_result = final_result
            plan.success = all(s.status == StepStatus.SUCCESS for s in plan.steps)
            
            # Store result in memory
            self.memory.add_conversation("assistant", final_result)
            self.memory.add_task(
                task=user_input,
                steps=[s.description for s in plan.steps],
                result=final_result,
                success=plan.success
            )
            
            # 🔥 Active Memory Extraction (非阻塞)
            asyncio.create_task(self._extract_memories(user_input, final_result))
            
            return final_result
            
        except Exception as e:
            error_msg = f"Agent error: {str(e)}"
            print(f"❌ {error_msg}")
            self.memory.add_conversation("assistant", error_msg, {"error": True})
            return error_msg
    
    async def handle_user_feedback(self, type: str, comment: str) -> str:
        """Handle explicit user feedback"""
        # Get last task from memory
        last_task = self.memory.task_history[-1] if self.memory.task_history else None
        
        if last_task:
            task_query = last_task.get("task", "unknown")
            steps = last_task.get("steps", [])
            # Assume last tool used
            last_tool = steps[-1] if steps else "unknown"
            
            self.feedback.record_feedback(task_query, last_tool, type, comment)
            return f"🙏 {type.title()} feedback recorded. I will learn from this."
        else:
            return "??? No recent task to learn from."
    
    async def _extract_memories(self, user_input: str, assistant_response: str) -> None:
        """
        提取并保存用户信息（异步，非阻塞）
        """
        try:
            from jarvis_assistant.core.memory_agent import get_memory_agent
            agent = get_memory_agent()
            await agent.analyze_and_extract(user_input, assistant_response)
        except Exception as e:
            # Silent fail - memory extraction should not break main flow
            print(f"⚠️ Memory extraction error: {e}")
    


    async def plan(self, user_input: str) -> ExecutionPlan:
        """
        Decompose user input into executable steps using LLM.
        Upgraded from keyword matching to intelligent planning.
        """
        plan = ExecutionPlan(task=user_input)
        
        # Build planning prompt with available tools and context
        history = self.get_history(limit=5)
        
        # 🔥 Get User Context (Hierarchical)
        context = self.memory.get_context_for_response()
        context_lines = []
        if context:
            if "project" in context:
                context_lines.append(f"**Current Project**: {context['project']}")
            if "learning" in context:
                context_lines.append(f"**Learning Focus**: {context['learning']}")
            if "research_area" in context:
                context_lines.append(f"**Research Area**: {context['research_area']}")
            if "location" in context:
                context_lines.append(f"**Location**: {context['location']}")
            if "name" in context:
                context_lines.append(f"**Name**: {context['name']}")
        
        context_str = "\n".join(context_lines) if context_lines else "暂无用户背景信息"
        
        tool_descriptions = "\n".join([
            f"- {name}: {tool.description}" 
            for name, tool in list(self.tools.items())[:20]
        ])
        
        planning_prompt = f"""You are Jarvis, a warm and intelligent assistant who truly knows the user.

[USER CONTEXT] (Use this background to personalize your responses)
{context_str}

**Personalization Guidelines**:
1. When answering questions, naturally use the user's background as examples when relevant
2. If the topic relates to their project/research, acknowledge the connection
3. Use a friendly, conversational tone (像朋友一样，不要用"您")
4. Don't mechanically repeat user info - weave it naturally into responses
5. Occasionally (not every time) show care about their ongoing projects

[CONVERSATION HISTORY]
{history}

[AVAILABLE TOOLS]
{tool_descriptions}

[USER REQUEST]
"{user_input}"

[INSTRUCTIONS]
1. Analyze if the user request requires tool usage based on history and intent.
2. If the user mentions updating their info (location, name, etc), use 'update_user_info'.
3. If user mentions a project/research/learning focus, it will be automatically saved.
4. For weather/location queries, prioritize the user's location from [USER CONTEXT] if no city is specified.
5. If tools are needed, respond with a JSON object containing the steps.
6. If it's a simple conversational response, return: {{"steps": []}}.

Response (JSON only):"""
        
        try:
            # Use simple keyword fallback first (fast path)
            matched_tools = []
            
            # --- CUSTOM INTENT KEYWORDS ---
            # Extend default intent matcher with user tools
            import re
            # Match "我在青岛市" or "我现在在青岛" or "去青岛"
            # Captures "青岛" from "在青岛市"
            loc_match = re.search(r"(?:我在|在|去)(.+?)[市区县]", user_input)
            if loc_match:
                 city = loc_match.group(1).replace("现在", "").replace("在", "").strip()
                 print(f"🚀 Fast Path: User Location Update -> {city}")
                 matched_tools.append(("update_user_info", {"key": "location", "value": city}))

            for keyword, tool_name in self.intent_keywords.items():
                if keyword in user_input:
                    # Special handling for weather without city
                    if tool_name == "get_weather":
                         # Check if city in input
                         # Simple check: if input length < 10 ("今天天气") -> use profile
                         if len(user_input) < 10 and "天气" in user_input:
                             profile_city = self.memory.get_profile("location")
                             if profile_city:
                                 matched_tools.append((tool_name, {"city": profile_city}))
                                 continue
                    
                    matched_tools.append((tool_name, {}))
            
            if matched_tools:
                # Fast keyword-based path
                for tool_name, forced_args in matched_tools:
                    tool_args = self._extract_args(user_input, tool_name)
                    tool_args.update(forced_args)  # 🔥 Apply profile args if any
                    
                    # 🔴 FIX #2: Handle multi-symbol stock queries
                    if tool_name == "get_stock_price" and "symbol" in tool_args:
                        symbols = tool_args["symbol"].split(",") if "," in tool_args["symbol"] else [tool_args["symbol"]]
                        for symbol in symbols:
                            step = PlanStep(
                                description=f"Execute {tool_name} for {symbol.strip()}",
                                tool_name=tool_name,
                                tool_args={"symbol": symbol.strip()}
                            )
                            plan.steps.append(step)
                    else:
                        # Single-step tool
                        step = PlanStep(
                            description=f"Execute {tool_name}",
                            tool_name=tool_name,
                            tool_args=tool_args
                        )
                        plan.steps.append(step)
            else:
                # No keyword match - try heuristic intent inference
                inferred = self._infer_intent(user_input)
                if inferred:
                    tool_name, tool_args = inferred
                    plan.steps.append(PlanStep(
                        description=f"Execute {tool_name}",
                        tool_name=tool_name,
                        tool_args=tool_args
                    ))
                else:
                    # 🔴 FAST PATH: Context continuation detection (skip Doubao for lower latency)
                    context_inferred = self._infer_from_context(user_input)
                    if context_inferred:
                        tool_name, tool_args = context_inferred
                        print(f"🚀 Context shortcut: {tool_name}")
                        plan.steps.append(PlanStep(
                            description=f"Execute {tool_name} (context)",
                            tool_name=tool_name,
                            tool_args=tool_args
                        ))
                    else:
                        # 🚀 FAST PATH: Detect pure conversational queries (no tools needed)
                        conversational_patterns = [
                            "记住", "记得", "我喜欢", "我想", "解释", "什么是", "为什么", 
                            "怎么样", "如何", "告诉我", "你觉得", "你认为", "聊聊"
                        ]
                        is_conversational = any(p in user_input for p in conversational_patterns)
                        
                        if is_conversational and len(user_input) < 50:
                            # Skip expensive Planner for obvious conversational queries
                            print("💬 Conversational query detected - skipping Planner")
                            plan.steps.append(PlanStep(
                                description="Respond conversationally",
                                tool_name=None
                            ))
                        else:
                            # Complex query - engage Doubao Planner
                            print("🧠 No keyword match. Engaging Cognitive Brain (Doubao)...")
                            llm_plan = await self._plan_with_doubao(user_input, planning_prompt)
                        
                        if llm_plan and llm_plan.get("steps"):
                            for s in llm_plan["steps"]:
                                plan.steps.append(PlanStep(
                                    description=s.get("description", "LLM Task"),
                                    tool_name=s.get("tool"),
                                    tool_args=s.get("args", {})
                                ))
                        else:
                            # Fallback
                            plan.steps.append(PlanStep(
                                description="Respond conversationally",
                                tool_name=None
                            ))
            
        except Exception as e:
            print(f"Planning error: {e}")
            plan.steps.append(PlanStep(
                description="Fallback: conversational response",
                tool_name=None
            ))
        
        return plan

    async def _plan_with_doubao(self, user_input: str, system_prompt: str) -> dict:
        """
        Call Doubao (Volcengine) HTTP API for planning using aiohttp for non-blocking IO.
        """
        import aiohttp
        import json
        import os
        
        api_key = os.getenv("DOUBAO_ARK_API_KEY")
        endpoint_id = os.getenv("DOUBAO_ENDPOINT_ID")
        
        if not api_key or not endpoint_id:
            print("⚠️ Missing Doubao API Key or Endpoint ID for HTTP Planner.")
            return None
            
        url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        payload = {
            "model": endpoint_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            "response_format": {"type": "json_object"}
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # 🚀 Flash model needs more time for complex planning (increased from 30s)
                async with session.post(url, headers=headers, json=payload, timeout=45) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print("✅ Doubao Planner Respond Success")
                        content = data['choices'][0]['message']['content']
                        if isinstance(content, str):
                            return json.loads(content)
                        return content
                    else:
                        text = await resp.text()
                        print(f"❌ Doubao HTTP Error: {text}")
                        return None
        except Exception as e:
            print(f"❌ Doubao Connection Error: {e}")
            return None

    def _infer_from_context(self, user_input: str) -> Optional[tuple]:
        """
        🚀 FAST PATH: Infer intent from conversation context without calling LLM.
        Used for follow-up queries like "那明天呢？" or "换一首"
        """
        import re
        text = user_input.strip()
        
        # Pattern 1: Time-based follow-up (明天、后天、昨天)
        time_patterns = ["明天", "后天", "昨天", "下周", "这周", "周末"]
        if any(t in text for t in time_patterns) or text in ["那明天呢", "那后天呢", "那呢"]:
            # Check last conversation topic
            last_topic = self._get_last_topic()
            if last_topic == "weather":
                city = self._get_last_city() or "Beijing"
                # 🔧 FIX: Use get_forecast for future dates, not get_weather
                if "明天" in text:
                    return ("get_forecast", {"city": city, "days": 2})  # Today + Tomorrow
                elif "后天" in text:
                    return ("get_forecast", {"city": city, "days": 3})  # Today + 2 days
                else:
                    return ("get_weather", {"city": city})
            elif last_topic == "stock":
                # Stock doesn't have "tomorrow" - just repeat query
                return ("get_stock_price", {"symbol": self._get_last_symbol() or "AAPL"})
        
        # Pattern 2: Music follow-up (换一首、下一首、上一首)
        music_patterns = ["换一首", "下一首", "上一首", "继续播放", "停"]
        for p in music_patterns:
            if p in text:
                if "停" in text:
                    return ("play_music", {"action": "stop"})
                else:
                    return ("play_music", {"action": "play"})  # Random next
        
        # Pattern 3: Generic "呢" follow-up
        if text.endswith("呢") or text.endswith("呢？"):
            last_topic = self._get_last_topic()
            if last_topic:
                # Reuse last tool with same args
                last_args = self._get_last_args()
                if last_topic == "weather":
                    return ("get_weather", last_args or {"city": "Beijing"})
                elif last_topic == "stock":
                    return ("get_stock_price", last_args or {"symbol": "AAPL"})
        
        return None
    
    def _get_last_topic(self) -> Optional[str]:
        """Get the topic of the last conversation turn"""
        if not self.memory.task_history:
            return None
        last_task = self.memory.task_history[-1]
        steps = last_task.get("steps", [])
        for step in steps:
            if "weather" in step.lower():
                return "weather"
            if "stock" in step.lower():
                return "stock"
            if "music" in step.lower():
                return "music"
        return None
    
    def _get_last_city(self) -> Optional[str]:
        """Extract city from last weather query"""
        if not self.memory.conversations:
            return None
        for msg in reversed(self.memory.conversations):
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                # Extract city from response like "北京天气：..."
                import re
                match = re.search(r'([^\s]+)天气', content)
                if match:
                    return match.group(1)
        return None
    
    def _get_last_symbol(self) -> Optional[str]:
        """Extract stock symbol from last query"""
        if not self.memory.conversations:
            return None
        for msg in reversed(self.memory.conversations):
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                import re
                match = re.search(r'（([A-Z]+)）', content)
                if match:
                    return match.group(1)
        return None
    
    def _get_last_args(self) -> Optional[dict]:
        """Get args from last successful tool call"""
        if not self.memory.task_history:
            return None
        last_task = self.memory.task_history[-1]
        # Simple extraction - could be improved
        return None
    
    def _infer_intent(self, user_input: str) -> Optional[tuple]:
        """Heuristic intent inference when no explicit keyword match exists."""
        import re
        text = user_input.strip()
        t = text.lower()
        scores = {}

        def add(tool: str, pts: int):
            if tool in self.tools:
                scores[tool] = scores.get(tool, 0) + pts

        is_question = any(x in text for x in ["?", "？", "吗", "么", "几", "多少", "要不要", "会不会"])

        # Math
        if re.search(r'[\d\.]+\s*[\+\-\*\/]\s*[\d\.]+', text) or any(op in text for op in ["加", "减", "乘", "除"]):
            add("calculate", 3)

        # Time
        if any(x in text for x in ["几点", "几时", "几点钟", "几点了", "现在几点", "时间", "现在是什么时候", "星期几", "日期"]):
            add("get_current_time", 3)

        # Reminders
        if "提醒" in text or re.search(r'\d+\s*(秒|分钟|分|小时|时)后', text):
            add("schedule_reminder", 3)

        # Weather
        weather_cues = ["天气", "气温", "温度", "冷", "热", "下雨", "雨", "雪", "刮风", "风大", "雾", "霾", "潮湿", "湿度", "外面", "出门", "带伞", "体感", "空气质量", "穿什么"]
        if any(c in text for c in weather_cues):
            add("get_weather", 2 if is_question else 1)
        if re.search(r'(几度|多少度|\d+\s*度|\d+\s*°)', text):
            add("get_weather", 2)

        # Thermostat
        thermo_cues = ["空调", "暖气", "制冷", "制热", "调到", "调温", "升温", "降温", "风速", "热一点", "冷一点"]
        if any(c in text for c in thermo_cues):
            add("control_thermostat", 3)

        # Lights (explicit on/off)
        if any(c in text for c in ["开灯", "打开灯", "关灯", "关掉灯", "把灯打开", "把灯关上", "亮一点", "暗一点"]):
            add("control_xiaomi_light", 3)

        # Music
        music_cues = ["音乐", "歌曲", "歌", "播放", "来首", "来点", "听点", "放点", "想听", "点一首"]
        if any(c in text for c in music_cues):
            add("play_music", 2)

        # News
        news_cues = ["新闻", "头条", "热点", "要闻", "最新消息", "发生了什么", "有什么大事", "快讯", "简报"]
        if any(c in text for c in news_cues):
            add("get_news", 2)

        # Stock/Crypto
        ticker_whitelist = {
            "nvda", "nvidia", "tsla", "tesla", "aapl", "apple", "msft", "microsoft",
            "baba", "alibaba", "tencent", "0700", "qqq", "spy", "btc", "eth", "amzn",
            "amazon", "meta", "goog", "googl", "google"
        }
        tokens = re.findall(r'\b[a-zA-Z0-9]{2,6}(?:-[a-zA-Z]{1,3})?\b', text)
        for tok in tokens:
            if tok.lower() in ticker_whitelist:
                add("get_stock_price", 3)
                break
        company_cues = ["英伟达", "英伟", "特斯拉", "特斯", "苹果", "微软", "阿里", "腾讯", "茅台", "比特币", "以太坊", "百度", "京东", "拼多多", "美团", "小米"]
        if any(c in text for c in company_cues):
            add("get_stock_price", 2)
        stock_cues = ["股价", "股票", "股市", "大盘", "涨跌", "行情", "走势", "币价", "数字货币", "币", "市值"]
        if any(c in text for c in stock_cues):
            add("get_stock_price", 2)

        # Web search (lowest priority)
        search_cues = ["搜索", "搜一下", "查一下", "帮我查", "帮我找", "资料", "百科", "是谁", "是什么", "怎么", "为什么", "教程", "官网", "地址"]
        if any(c in text for c in search_cues):
            add("web_search", 1)

        if not scores:
            return None

        tool_name = max(scores.items(), key=lambda kv: kv[1])[0]
        if scores[tool_name] < 2 and tool_name != "web_search":
            return None

        return tool_name, self._extract_args(user_input, tool_name)
    
    def _extract_args(self, user_input: str, tool_name: str) -> Dict[str, Any]:
        """Extract tool arguments from user input"""
        args = {}
        
        if tool_name == "get_weather":
            # flexible extraction: "查询[city]的天气"
            import re
            city = None
            
            # 🔴 FIX #3: Don't extract time words as locations
            time_words = ["今天", "明天", "后天", "昨天", "晚上", "中午", "早上", "下午", "傍晚"]
            
            match = re.search(r'(?:查询|查看|获取)?(.+?)的?天[气候]', user_input)
            if match:
                city_candidate = match.group(1).strip()
                # Clean up strict prefixes if user said "查询北京天气" -> "北京"
                for prefix in ["查询", "查看", "获取"]:
                    if city_candidate.startswith(prefix):
                        city_candidate = city_candidate[len(prefix):]
                
                # 🔴 CRITICAL: Don't use time words as city names
                if city_candidate not in time_words:
                    city = city_candidate
            
            if not city:
                # Heuristic fallback (handles "外面冷吗", "上海多少度" etc.)
                city = IntentMatcher.match_weather(user_input)
                if city in time_words:
                    city = None
            
            # 🔴 FIX #3: Default to None (tool has Beijing default)
            args["city"] = city or None
        
        elif tool_name == "calculate":
            # Extract expression (support Chinese operators)
            import re
            expr = user_input.replace("乘以", "*").replace("乘", "*")
            expr = expr.replace("除以", "/").replace("除", "/")
            expr = expr.replace("加", "+").replace("减", "-")
            match = re.search(r'[\d\+\-\*\/\(\)\.]+', expr)
            if match:
                args["expression"] = match.group().strip()

        elif tool_name == "get_stock_price":
            import re
            
            # 🔴 FIX #1: Multi-entity detection for "X和Y", "X以及Y", "X跟Y"
            text = user_input
            symbols = []
            
            # Company name to symbol mapping
            company_map = {
                "特斯拉": "TSLA", "苹果": "AAPL", "微软": "MSFT", 
                "英伟达": "NVDA", "亚马逊": "AMZN", "谷歌": "GOOG",
                "阿里": "BABA", "腾讯": "0700.HK", "茅台": "600519.SS",
                "比特币": "BTC-USD", "以太坊": "ETH-USD", "黄金": "GC=F"
            }
            
            # Pattern 1: "X和Y" compound queries
            compound_pattern = r'([^\s，,。.]+?)(?:和|以及|跟|与)([^\s，,。.]+)'
            match = re.search(compound_pattern, text)
            if match:
                entity1 = match.group(1).strip()
                entity2 = match.group(2).strip()
                
                # Clean up: remove "查询", "的股价" etc.
                for prefix in ["查询", "查看", "获取"]:
                    entity1 = entity1.replace(prefix, "").strip()
                    entity2 = entity2.replace(prefix, "").strip()
                for suffix in ["股价", "的股价", "的", "价格", "行情"]:
                    entity1 = entity1.replace(suffix, "").strip()
                    entity2 = entity2.replace(suffix, "").strip()
                
                # Map to symbols
                symbol1 = company_map.get(entity1, entity1.upper() if re.match(r'^[A-Z]{1,5}$', entity1.upper()) else entity1)
                symbol2 = company_map.get(entity2, entity2.upper() if re.match(r'^[A-Z]{1,5}$', entity2.upper()) else entity2)
                
                symbols = [symbol1, symbol2]
            else:
                # Pattern 2: Try to extract ticker (e.g., NVDA, BRK-B)
                m = re.search(r'\b[a-zA-Z]{1,6}(?:-[a-zA-Z]{1,3})?\b', user_input)
                if m:
                    symbols = [m.group(0).upper()]
                else:
                    # Pattern 3: Company name extraction
                    q = user_input
                    for w in ["股价", "币价", "行情", "走势", "价格", "查询", "查看", "现在", "最新", "多少", "怎么样", "如何", "咋样", "情况", "的"]:
                        q = q.replace(w, "")
                    q = q.strip()
                    
                    # Check if it's a known company
                    symbol = company_map.get(q, q.upper() if q else user_input.strip())
                    symbols = [symbol]
            
            # Store as comma-separated if multiple
            args["symbol"] = symbols[0] if len(symbols) == 1 else ",".join(symbols)

        elif tool_name == "get_news":
            # Determine category
            category = "world"
            if any(k in user_input for k in ["财经", "金融", "股市", "商业", "finance", "business"]):
                category = "finance"
            args["category"] = category

        elif tool_name == "web_search":
            args["query"] = IntentMatcher.match_web_search(user_input)
            args["num_results"] = 3
        
        elif tool_name == "play_music":
            action, query = IntentMatcher.match_music(user_input)
            if action == "stop":
                args["action"] = "stop"
            elif action == "list":
                args["action"] = "list"
            elif action == "play_random":
                args["action"] = "play"
            elif action == "play_specific":
                args["action"] = "play"
                args["query"] = query
            else:
                # Fallback
                if "停" in user_input or "关" in user_input:
                    args["action"] = "stop"
                else:
                    args["action"] = "play"

        elif tool_name == "control_xiaomi_light":
            import re
            action = IntentMatcher.match_light_control(user_input)
            if action in ["on", "off"]:
                args["action"] = action
            elif "亮" in user_input or "暗" in user_input:
                args["action"] = "brightness"
                # default brightness
                value = 80 if "亮" in user_input else 30
                m = re.search(r'(\d{1,3})', user_input)
                if m:
                    value = int(m.group(1))
                args["value"] = max(1, min(100, value))

        elif tool_name == "read_file":
            import re
            match = re.search(r'读取文件\s*([^\s]+)', user_input)
            if match: args["path"] = match.group(1)
            
        elif tool_name == "write_file":
            import re
            match = re.search(r'写入文件\s*([^\s]+)\s*(.+)', user_input)
            if match:
                args["path"] = match.group(1)
                args["content"] = match.group(2)
                
        elif tool_name == "list_dir":
            import re
            match = re.search(r'查看目录\s*([^\s]+)', user_input)
            if match: args["path"] = match.group(1)
            
        elif tool_name == "send_email":
            # Basic extraction for simulation
            args["to"] = "user@example.com"
            args["subject"] = "Jarvis Notification"
            args["body"] = user_input
            
        elif tool_name == "add_calendar_event":
            args["event"] = user_input
            args["time"] = "明天"
            
        elif tool_name == "schedule_reminder":
            import re
            # Parse delay: "5秒后", "10分钟后"
            delay = 0
            match = re.search(r'(\d+)\s*(秒|分钟|分|小时|时)', user_input)
            if match:
                val = int(match.group(1))
                unit = match.group(2)
                if unit in ["秒"]: delay = val
                elif unit in ["分钟", "分"]: delay = val * 60
                elif unit in ["小时", "时"]: delay = val * 3600
            
            args["delay_seconds"] = max(delay, 5) # Minimum 5s
            
            # Parse description: remove trigger words and time
            desc = user_input
            for rm in ["提醒", "我", "后", match.group(0) if match else ""]:
                desc = desc.replace(rm, "")
            args["description"] = desc.strip() or "Reminder"
        
        return args
    
    async def execute_step(self, step: PlanStep, stream_callback: Optional[callable] = None) -> Optional[str]:
        """Execute a single plan step"""
        if step.tool_name is None:
            # For conversational steps, use LLM to generate response if not already present
            if not step.result or step.result == "Conversation response (no tool needed)":
                history = self.get_history(limit=5)
                prompt = f"""You are Jarvis. Respond to the user's request naturally.
[HISTORY]
{history}
[REQUEST]
{step.description}
"""
                step.result = await self._generate_conversational_response(prompt, stream_callback)
            step.status = StepStatus.SUCCESS
            return step.result
        
        if step.tool_name not in self.tools:
            step.status = StepStatus.FAILED
            step.error = f"Unknown tool: {step.tool_name}"
            return None
        
        try:
            tool = self.tools[step.tool_name]
            result = await tool.execute(**step.tool_args)
            
            # 🔴 CRITICAL: Validate tool result to prevent hallucination
            if result is None or str(result).startswith("❌") or "Error" in str(result) or "error" in str(result):
                step.status = StepStatus.FAILED
                step.error = str(result) if result else "Tool returned empty result"
                step.result = None
                return None
            
            step.status = StepStatus.SUCCESS
            step.result = str(result)
            return step.result
        except Exception as e:
            step.status = StepStatus.FAILED
            step.error = str(e)
            return None

    def _get_personalized_system_prompt(self) -> str:
        """Build a personalized system prompt from user memory"""
        profile = self.memory.get_all_profile()
        basics = profile.get("basics", {})
        focus = profile.get("current_focus", {})
        interests = profile.get("interests", {})
        
        prompt = [
            "You are JARVIS, a helpful and sophisticated AI assistant.",
            "Your tone should be warm, intelligent, and natural, like a trusted friend (not overly formal).",
            "",
            "=== USER CONTEXT (USE THIS NATURALLY) ===",
        ]
        
        if basics.get("name"):
            prompt.append(f"- User Name: {basics['name']}")
        if basics.get("location"):
            prompt.append(f"- Location: {basics['location']}")
            
        if focus:
            prompt.append("- Current Focus/Projects:")
            for key, item in focus.items():
                if isinstance(item, dict) and "value" in item:
                    # New weighted format
                    prompt.append(f"  * {key}: {item['value']} (Mentioned {item.get('count', 1)} times)")
                else:
                    prompt.append(f"  * {key}: {item}")
        
        if interests:
            prompt.append("- Interests & Preferences:")
            for key, val in interests.items():
                prompt.append(f"  * {key}: {val}")
                
        prompt.extend([
            "",
            "=== INSTRUCTIONS ===",
            "1. Reference the user's focus/projects NATURALLY in a conversational way if relevant.",
            "2. Occasionally (but not every time) offer encouragement or ask about their progress.",
            "3. If the user asks who they are or what you remember, summarize this profile.",
            "4. Keep your responses concise and engaging for a voice interface.",
            "5. If you cannot answer a factual question (weather, stock, etc.) without tools, admit you need a tool.",
        ])
        
        return "\n".join(prompt)

    async def _generate_conversational_response(self, user_query: str, stream_callback: Optional[callable] = None) -> str:
        """
        Generate personalized conversational response using Doubao Realtime API.
        🚀 OPTIMIZED: Uses /api/v3/responses with SSE streaming for sub-1s TTFT
        """
        import aiohttp
        import os
        import json
        import time
        
        api_key = os.getenv("DOUBAO_ARK_API_KEY")
        endpoint_id = os.getenv("DOUBAO_ENDPOINT_ID")
        
        if not api_key or not endpoint_id:
            # Fallback for demo
            context = self.memory.get_context_for_response()
            if "深度学习" in user_query and context.get("learning") == "深度学习":
                return "好的，深度学习是一个非常有挑战但也非常有成就感的领域，我会陪你一起攻克它！"
            return "收到，先生。我会记在心里。"

        # Build input with conversation history (Responses API format)
        raw_history = self.memory.get_context(limit=6)
        
        # Convert to Responses API input format
        input_messages = []
        
        # Add conversation history
        role_map = {"user": "user", "assistant": "assistant", "bot": "assistant"}
        for entry in raw_history:
            role = role_map.get(entry['role'], "user")
            content = entry['content']
            if role == "user" and content == user_query:
                continue
            
            msg = {
                "type": "message", # 🔥 REQUIRED FOR RESPONSES API
                "role": role,
                "content": [{"type": "input_text" if role == "user" else "output_text", "text": content}]
            }
            if role == "assistant":
                msg["status"] = "completed"
            
            input_messages.append(msg)
        
        # Add current query
        input_messages.append({
            "type": "message", # 🔥 REQUIRED FOR RESPONSES API
            "role": "user",
            "content": [{"type": "input_text", "text": user_query}]
        })

        # 🚀 Use Responses API with THINKING DISABLED for ultra-low latency
        url = "https://ark.cn-beijing.volces.com/api/v3/responses"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Optimization payload based on provided documentation
        payload = {
            "model": endpoint_id,
            "input": input_messages,
            "stream": True,
            "temperature": 0.7,
            "thinking": {
                "type": "disabled" # 🔥 TURN OFF REASONING FOR SPEED
            }
        }
        
        # Only add reasoning.effort for supported models
        if "lite" in endpoint_id or "251228" in endpoint_id or "251015" in endpoint_id:
            payload["reasoning"] = {"effort": "minimal"}
        
        full_content = ""
        first_token_received = False
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=30) as resp:
                    if resp.status == 200:
                        print("🧠 [Brain] Streaming...", end="", flush=True)
                        
                        async for line in resp.content:
                            line_str = line.decode('utf-8').strip()
                            
                            if not line_str or not line_str.startswith('data:'):
                                continue
                            
                            data_str = line_str[5:].strip()
                            if data_str == '[DONE]':
                                break
                            
                            try:
                                data = json.loads(data_str)
                                event_type = data.get('type', '')
                                
                                # ✅ Only process output_text delta events
                                if event_type == 'response.output_text.delta':
                                    chunk = data.get('delta', '')
                                    if chunk:
                                        if not first_token_received:
                                            first_token_received = True
                                            # print("", flush=True)  # Still need newline for first token
                                        full_content += chunk
                                        print(chunk, end="", flush=True)
                                        
                                        # 🚀 Invoke callback for streaming TTS
                                        if stream_callback:
                                            try:
                                                import inspect
                                                if inspect.iscoroutinefunction(stream_callback):
                                                    await stream_callback(chunk)
                                                else:
                                                    stream_callback(chunk)
                                            except Exception as cb_e:
                                                print(f"⚠️ Callback error: {cb_e}")
                                            
                            except json.JSONDecodeError:
                                pass
                        
                        print(" ✅")
                        return full_content.strip()
                    else:
                        error_text = await resp.text()
                        print(f"❌ Realtime API Error ({resp.status}): {error_text}")
                        
        except Exception as e:
            print(f"❌ Realtime API connection error: {e}")
            
        return full_content.strip() if full_content else "收到，先生。我会继续关注您的需求。"
    
    def synthesize(self, plan: ExecutionPlan) -> str:
        """Combine step results into final response"""
        if not plan.steps:
            return "I couldn't understand your request."
        
        results = []
        failed_count = 0
        
        # Check if this is a multi-stock query
        stock_steps = [s for s in plan.steps if s.tool_name == "get_stock_price" and s.status == StepStatus.SUCCESS]
        
        if len(stock_steps) > 1:
            # 🎯 Smart merging for multiple stock queries
            stock_data = []
            for step in stock_steps:
                result = step.result
                # Extract the actual price data (remove redundant comments)
                # Format: "评论。 公司（代码）现价 X USD，今日上涨/下跌了 Y%。"
                import re
                match = re.search(r'([^\。]+（[^\)]+）现价[^。]+。)', result)
                if match:
                    stock_data.append(match.group(1))
                else:
                    stock_data.append(result)
            
            # Combine all stocks in one sentence
            combined = " ".join(stock_data)
            results.append(combined)
            
            # Process remaining non-stock steps
            for step in plan.steps:
                if step.tool_name != "get_stock_price":
                    if step.status == StepStatus.SUCCESS and step.result:
                        results.append(step.result)
                    elif step.status == StepStatus.FAILED:
                        failed_count += 1
                        if step.tool_name:
                            error_msg = step.error or "unknown error"
                            results.append(f"抱歉，{step.tool_name}执行失败: {error_msg}")
                        else:
                            results.append(f"⚠️ {step.description} failed")
        else:
            # Normal synthesis for single-step or non-stock queries
            for step in plan.steps:
                if step.status == StepStatus.SUCCESS and step.result:
                    results.append(step.result)
                elif step.status == StepStatus.FAILED:
                    failed_count += 1
                    # 🔴 CRITICAL: Be honest about failures - don't hallucinate success
                    if step.tool_name:
                        error_msg = step.error or "unknown error"
                        results.append(f"抱歉，{step.tool_name}执行失败: {error_msg}")
                    else:
                        results.append(f"⚠️ {step.description} failed")
        
        # If ALL steps failed, give a clearer error message
        if failed_count == len(plan.steps):
            return "抱歉，我无法完成这个请求。" + ("\n".join(results) if results else "")
        
        base_response = "\n".join(results) if results else "Task completed."
        
        # 🔥 Personalization Enhancement
        enhanced_response = self._add_personal_touch(base_response)
        
        return enhanced_response
    
    def _add_personal_touch(self, response: str) -> str:
        """
        偶尔在回复中加入关心语句（基础20%概率，随提及次数增加）
        """
        import random
        
        # Skip if response is too short (likely a simple acknowledgment)
        if len(response) < 10:
            return response
        
        # Skip if it's an error message
        if "抱歉" in response or "失败" in response or "错误" in response:
            return response
        
        # Get context (with counts)
        context = self.memory.get_context_for_response()
        
        # Calculate dynamic probability based on mention counts
        # Base: 20%, +10% for each additional mention (max 80%)
        base_prob = 0.2
        max_count = max(
            context.get("project_count", 0),
            context.get("learning_count", 0),
            context.get("research_area_count", 0)
        )
        
        if max_count > 1:
            # Increase probability: 20% + 10% * (count-1), capped at 80%
            trigger_prob = min(0.8, base_prob + 0.1 * (max_count - 1))
        else:
            trigger_prob = base_prob
        
        # Random check
        if random.random() > trigger_prob:
            return response
        
        # Generate caring phrase based on context
        caring_phrases = []
        
        if "project" in context:
            caring_phrases = [
                f"\n\n对了，{context['project']}进展顺利吗？",
                f"\n\n论文写得怎么样了？",
                ""  # Empty = no addition sometimes
            ]
        elif "learning" in context:
            caring_phrases = [
                f"\n\n{context['learning']}学得怎么样了？",
                f"\n\n最近学习有什么新收获吗？",
                ""
            ]
        
        if caring_phrases:
            phrase = random.choice(caring_phrases)
            if phrase:  # Only add if not empty
                return response + phrase
        
        return response
    
    def get_history(self, limit: int = 5) -> str:
        """Get conversation history"""
        return self.memory.get_context_string(limit)


# Singleton instance
_agent_instance: Optional[JarvisAgent] = None


def get_agent() -> JarvisAgent:
    """Get the global agent instance"""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = JarvisAgent()
    return _agent_instance


# Quick test
if __name__ == "__main__":
    async def test():
        agent = get_agent()
        
        # Test 1: Time
        result = await agent.run("现在几点了")
        print(f"Result: {result}\n")
        
        # Test 2: Weather
        result = await agent.run("北京天气怎么样")
        print(f"Result: {result}\n")
        
        # Test 3: Calculate
        result = await agent.run("计算 123 * 456")
        print(f"Result: {result}\n")
        
        # Test 4: History
        print("History:", agent.get_history())
    
    asyncio.run(test())
