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
    
    async def execute(self, **kwargs) -> str:
        """Get weather for specified city using wttr.in (free, no API key needed)"""
        city = kwargs.get("city", "Beijing")
        async def fetch_open_meteo(city_name: str) -> str:
            # Fallback: Open-Meteo (no API key)
            try:
                geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}&count=1&language=zh&format=json"
                async with aiohttp.ClientSession() as session:
                    async with session.get(geo_url, timeout=10) as resp:
                        if resp.status != 200:
                            return f"抱歉，我现在连不上天气服务，暂时无法获取 {city_name} 的天气，请稍后再试。"
                        geo = await resp.json()
                        results = geo.get("results") or []
                        if not results:
                            return f"抱歉，我没有找到 {city_name} 的位置。"
                        lat = results[0]["latitude"]
                        lon = results[0]["longitude"]

                    weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
                    async with session.get(weather_url, timeout=10) as resp2:
                        if resp2.status != 200:
                            return f"抱歉，我现在连不上天气服务，暂时无法获取 {city_name} 的天气，请稍后再试。"
                        data = await resp2.json()
                        cw = data.get("current_weather") or {}
                        temp_c = cw.get("temperature", "N/A")
                        wind_speed = cw.get("windspeed", "N/A")
                        code = cw.get("weathercode")
                        code_map = {
                            0: "晴朗", 1: "多云", 2: "多云", 3: "阴",
                            45: "雾", 48: "雾", 51: "小毛毛雨", 53: "毛毛雨", 55: "毛毛雨",
                            61: "小雨", 63: "中雨", 65: "大雨",
                            71: "小雪", 73: "中雪", 75: "大雪",
                            80: "阵雨", 81: "阵雨", 82: "暴雨",
                            95: "雷暴"
                        }
                        desc_cn = code_map.get(code, "未知")
                        return (
                            f"{city_name}天气：{desc_cn}，"
                            f"温度{temp_c}度，"
                            f"风速{wind_speed}公里每小时。"
                        )
            except Exception:
                return f"抱歉，我现在连不上天气服务，暂时无法获取 {city_name} 的天气，请稍后再试。"

        try:
            url = f"https://wttr.in/{city}?format=j1&lang=zh"
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
                            f"{city}天气：{desc_cn}，"
                            f"温度{temp_c}度，体感{feels_like}度，"
                            f"湿度{humidity}%，"
                            f"风速{wind_speed}公里每小时。"
                        )
                    # fallback
                    return await fetch_open_meteo(city)
        except Exception:
            # Comfort-first: no stack traces, no scary errors.
            return await fetch_open_meteo(city)


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
    
    async def execute(self, **kwargs) -> str:
        """Get weather forecast"""
        city = kwargs.get("city", "Beijing")
        days = kwargs.get("days", 3)
        try:
            url = f"https://wttr.in/{city}?format=j1&lang=zh"
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
        except Exception:
            return f"抱歉，我现在连不上天气服务，暂时无法获取 {city} 的天气预报，请稍后再试。"
