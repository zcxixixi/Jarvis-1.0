"""
Jarvis Agent Core
Autonomous agent with planning, execution, and verification loop.
"""

import asyncio
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

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
    
    async def run(self, user_input: str) -> str:
        """
        Main agent loop with Self-Learning
        """
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
                
                result = await self.execute_step(step)
                
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
    


    async def plan(self, user_input: str) -> ExecutionPlan:
        """
        Decompose user input into executable steps using LLM.
        Upgraded from keyword matching to intelligent planning.
        """
        plan = ExecutionPlan(task=user_input)
        
        # Build planning prompt with available tools and context
        history = self.get_history(limit=5)
        
        tool_descriptions = "\n".join([
            f"- {name}: {tool.description}" 
            for name, tool in list(self.tools.items())[:15]
        ])
        
        planning_prompt = f"""You are Jarvis, a highly intelligent autonomous assistant. 
Your goal is to fulfill the user request by planning and executing steps using available tools.

[CONVERSATION HISTORY]
{history}

[AVAILABLE TOOLS]
{tool_descriptions}

[USER REQUEST]
"{user_input}"

[INSTRUCTIONS]
1. Analyze if the user request requires tool usage based on history and intent.
2. If tools are needed, respond with a JSON object containing the steps.
3. If it's a simple conversational response, return: {{"steps": []}}.
4. Keep the plan minimal and efficient.

Response (JSON only):"""
        
        try:
            # Use simple keyword fallback first (fast path)
            matched_tools = []
            for keyword, tool_name in self.intent_keywords.items():
                if keyword in user_input:
                    if tool_name not in matched_tools:
                        matched_tools.append(tool_name)
            
            if matched_tools:
                # Fast keyword-based path
                for tool_name in matched_tools:
                    step = PlanStep(
                        description=f"Execute {tool_name}",
                        tool_name=tool_name,
                        tool_args=self._extract_args(user_input, tool_name)
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
                    # No heuristic match - try Doubao LLM (Cognitive Brain)
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
                async with session.post(url, headers=headers, json=payload, timeout=8) as resp:
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
            match = re.search(r'(?:查询|查看|获取)?(.+?)的?天[气候]', user_input)
            if match:
                city_candidate = match.group(1).strip()
                # Clean up strict prefixes if user said "查询北京天气" -> "北京"
                for prefix in ["查询", "查看", "获取"]:
                    if city_candidate.startswith(prefix):
                        city_candidate = city_candidate[len(prefix):]
                city = city_candidate
            if not city:
                # Heuristic fallback (handles "外面冷吗", "上海多少度" etc.)
                city = IntentMatcher.match_weather(user_input)
            args["city"] = city or "北京"
        
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
            # Try to extract ticker (e.g., NVDA, BRK-B), case-insensitive
            m = re.search(r'\b[a-zA-Z]{1,6}(?:-[a-zA-Z]{1,3})?\b', user_input)
            if m:
                args["symbol"] = m.group(0).upper()
            else:
                q = user_input
                for w in ["股价", "币价", "行情", "走势", "价格", "查询", "查看", "现在", "最新", "多少", "怎么样", "如何", "咋样", "情况"]:
                    q = q.replace(w, "")
                args["symbol"] = q.strip() or user_input.strip()

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
    
    async def execute_step(self, step: PlanStep) -> Optional[str]:
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
                step.result = await self._generate_conversational_response(prompt)
            step.status = StepStatus.SUCCESS
            return step.result
        
        if step.tool_name not in self.tools:
            step.status = StepStatus.FAILED
            step.error = f"Unknown tool: {step.tool_name}"
            return None
        
        try:
            tool = self.tools[step.tool_name]
            result = await tool.execute(**step.tool_args)
            step.status = StepStatus.SUCCESS
            step.result = str(result)
            return step.result
        except Exception as e:
            step.status = StepStatus.FAILED
            step.error = str(e)
            return None

    async def _generate_conversational_response(self, prompt: str) -> str:
        """Helper to generate plain text response from Doubao"""
        import aiohttp
        import os
        
        api_key = os.getenv("DOUBAO_ARK_API_KEY")
        endpoint_id = os.getenv("DOUBAO_ENDPOINT_ID")
        
        if not api_key or not endpoint_id:
            return "I'm sorry, I'm having trouble connecting to my brain right now."

        url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "model": endpoint_id,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=8) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data['choices'][0]['message']['content']
        except Exception:
            pass
        return "Understood, sir."
    
    def synthesize(self, plan: ExecutionPlan) -> str:
        """Combine step results into final response"""
        if not plan.steps:
            return "I couldn't understand your request."
        
        results = []
        for step in plan.steps:
            if step.status == StepStatus.SUCCESS and step.result:
                results.append(step.result)
            elif step.status == StepStatus.FAILED:
                results.append(f"⚠️ {step.description} failed: {step.error}")
        
        return "\n".join(results) if results else "Task completed."
    
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
