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
        """Get weather for specified city - optimized for speed"""
        city = kwargs.get("city", "Beijing")
        
        # Try wttr.in with SHORT timeout (it's usually fast or fails)
        try:
            url = f"https://wttr.in/{city}?format=j1&lang=zh"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=3) as response:  # 3s timeout
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
        except Exception:
            pass  # Fall through to backup
        
        # Fallback: Open-Meteo (more reliable but needs 2 requests)
        try:
            # Pre-defined coordinates for common cities (skip geocoding)
            city_coords = {
                "北京": (39.9042, 116.4074), "beijing": (39.9042, 116.4074),
                "上海": (31.2304, 121.4737), "shanghai": (31.2304, 121.4737),
                "深圳": (22.5431, 114.0579), "shenzhen": (22.5431, 114.0579),
                "广州": (23.1291, 113.2644), "guangzhou": (23.1291, 113.2644),
                "杭州": (30.2741, 120.1551), "hangzhou": (30.2741, 120.1551),
            }
            
            lat, lon = city_coords.get(city.lower(), (None, None))
            
            async with aiohttp.ClientSession() as session:
                # If city not in cache, do geocoding
                if lat is None:
                    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=zh&format=json"
                    async with session.get(geo_url, timeout=3) as resp:
                        if resp.status == 200:
                            geo = await resp.json()
                            results = geo.get("results") or []
                            if results:
                                lat = results[0]["latitude"]
                                lon = results[0]["longitude"]
                
                if lat is None:
                    return f"抱歉，我没有找到 {city} 的位置。"
                
                weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
                async with session.get(weather_url, timeout=3) as resp2:
                    if resp2.status == 200:
                        data = await resp2.json()
                        cw = data.get("current_weather") or {}
                        temp_c = cw.get("temperature", "N/A")
                        wind_speed = cw.get("windspeed", "N/A")
                        code = cw.get("weathercode")
                        code_map = {
                            0: "晴朗", 1: "晴", 2: "多云", 3: "阴",
                            45: "雾", 48: "雾", 51: "小雨", 53: "小雨", 55: "小雨",
                            61: "小雨", 63: "中雨", 65: "大雨",
                            71: "小雪", 73: "中雪", 75: "大雪",
                            80: "阵雨", 81: "阵雨", 82: "暴雨",
                            95: "雷暴"
                        }
                        desc_cn = code_map.get(code, "未知")
                        return (
                            f"{city}天气：{desc_cn}，"
                            f"温度{temp_c}度，"
                            f"风速{wind_speed}公里每小时。"
                        )
        except Exception:
            pass
        
        return f"抱歉，暂时无法获取 {city} 的天气，请稍后再试。"


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
        """Get weather forecast - with Open-Meteo fallback"""
        city = kwargs.get("city", "Beijing")
        days = kwargs.get("days", 3)
        
        # 1. Try wttr.in (Fast / Rich Text)
        try:
            url = f"https://wttr.in/{city}?format=j1&lang=zh"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=3) as response:
                    if response.status == 200:
                        data = await response.json()
                        forecasts = data.get("weather", [])[:days]
                        
                        result = f"📅 {city}未来{len(forecasts)}天天气预报：\n"
                        for day in forecasts:
                            date = day.get("date", "")
                            max_temp = day.get("maxtempC", "N/A")
                            min_temp = day.get("mintempC", "N/A")
                            hourly = day.get("hourly", [{}])
                            midday = hourly[len(hourly)//2] if hourly else {}
                            desc = midday.get("lang_zh", [{}])[0].get("value", "未知")
                            result += f"\n{date}: {desc}, {min_temp}°C ~ {max_temp}°C"
                        return result
        except Exception:
            pass

        # 2. Fallback: Open-Meteo (Reliable)
        try:
            # Re-use city coordinates cache if possible (simple dict for now)
            city_coords = {
                "北京": (39.9042, 116.4074), "beijing": (39.9042, 116.4074),
                "上海": (31.2304, 121.4737), "shanghai": (31.2304, 121.4737),
                "深圳": (22.5431, 114.0579), "shenzhen": (22.5431, 114.0579),
                "广州": (23.1291, 113.2644), "guangzhou": (23.1291, 113.2644),
                "杭州": (30.2741, 120.1551), "hangzhou": (30.2741, 120.1551),
            }
            lat, lon = city_coords.get(city.lower(), (None, None))

            async with aiohttp.ClientSession() as session:
                if lat is None:
                    # Geocoding
                    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=zh&format=json"
                    async with session.get(geo_url, timeout=3) as resp:
                        if resp.status == 200:
                            geo = await resp.json()
                            results = geo.get("results") or []
                            if results:
                                lat = results[0]["latitude"]
                                lon = results[0]["longitude"]
                
                if lat is None:
                    return f"抱歉，我没有找到 {city} 的位置。"

                # Forecast API
                weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=weathercode,temperature_2m_max,temperature_2m_min&timezone=auto"
                async with session.get(weather_url, timeout=3) as resp2:
                    if resp2.status == 200:
                        data = await resp2.json()
                        daily = data.get("daily", {})
                        
                        dates = daily.get("time", [])[:days]
                        codes = daily.get("weathercode", [])[:days]
                        maxs = daily.get("temperature_2m_max", [])[:days]
                        mins = daily.get("temperature_2m_min", [])[:days]

                        result = f"📅 {city}未来{len(dates)}天天气预报：\n"
                        
                        code_map = {
                            0: "晴朗", 1: "晴", 2: "多云", 3: "阴",
                            45: "雾", 48: "雾", 51: "小雨", 53: "小雨", 61: "小雨",
                            63: "中雨", 65: "大雨", 71: "小雪", 80: "阵雨", 95: "雷暴"
                        }

                        for i, date in enumerate(dates):
                            desc = code_map.get(codes[i], "未知")
                            result += f"\n{date}: {desc}, {mins[i]}°C ~ {maxs[i]}°C"
                        return result
        except Exception:
            pass

        return f"抱歉，暂时无法获取 {city} 的天气预报，请稍后再试。"
