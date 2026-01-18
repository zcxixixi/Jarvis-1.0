"""
Weather Tools
Provides weather-related functionality using free APIs
"""
import aiohttp
from typing import Dict, Any
from .base import BaseTool


class GetWeatherTool(BaseTool):
    """Get current weather for a city"""
    
    @property
    def name(self) -> str:
        return "get_weather"
    
    @property
    def description(self) -> str:
        return "获取指定城市的当前天气信息"
    
    def get_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "城市名称，例如：北京、上海、深圳"
                        }
                    },
                    "required": ["city"]
                }
            }
        }
    
    async def execute(self, city: str) -> str:
        """Get weather for specified city using wttr.in (free, no API key needed)"""
        try:
            url = f"https://wttr.in/{city}?format=j1"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        current = data.get("current_condition", [{}])[0]
                        
                        temp_c = current.get("temp_C", "N/A")
                        feels_like = current.get("FeelsLikeC", "N/A")
                        humidity = current.get("humidity", "N/A")
                        desc_cn = current.get("lang_zh", [{}])[0].get("value", current.get("weatherDesc", [{}])[0].get("value", "未知"))
                        wind_speed = current.get("windspeedKmph", "N/A")
                        
                        return (
                            f"🌡️ {city}天气：{desc_cn}\n"
                            f"温度：{temp_c}°C（体感 {feels_like}°C）\n"
                            f"湿度：{humidity}%\n"
                            f"风速：{wind_speed} km/h"
                        )
                    else:
                        return f"无法获取{city}的天气信息"
        except Exception as e:
            return f"获取天气时出错：{str(e)}"


class GetForecastTool(BaseTool):
    """Get weather forecast for a city"""
    
    @property
    def name(self) -> str:
        return "get_forecast"
    
    @property
    def description(self) -> str:
        return "获取指定城市未来几天的天气预报"
    
    def get_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "城市名称"
                        },
                        "days": {
                            "type": "integer",
                            "description": "预报天数（1-3）",
                            "enum": [1, 2, 3]
                        }
                    },
                    "required": ["city"]
                }
            }
        }
    
    async def execute(self, city: str, days: int = 3) -> str:
        """Get weather forecast"""
        try:
            url = f"https://wttr.in/{city}?format=j1"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        forecasts = data.get("weather", [])[:days]
                        
                        result = f"📅 {city}未来{len(forecasts)}天天气预报：\n"
                        for day in forecasts:
                            date = day.get("date", "")
                            max_temp = day.get("maxtempC", "N/A")
                            min_temp = day.get("mintempC", "N/A")
                            hourly = day.get("hourly", [{}])
                            # Get midday weather description
                            midday = hourly[len(hourly)//2] if hourly else {}
                            desc = midday.get("lang_zh", [{}])[0].get("value", "未知")
                            
                            result += f"\n{date}: {desc}, {min_temp}°C ~ {max_temp}°C"
                        
                        return result
                    else:
                        return f"无法获取{city}的天气预报"
        except Exception as e:
            return f"获取天气预报时出错：{str(e)}"
