"""
JARVIS Tools Module
Extensible tool system for JARVIS capabilities

This module provides all the tools (skills) that JARVIS can use.
Tools are selected automatically by the LLM based on user intent.
"""

from .base import BaseTool

# Time Tools
from .time_tools import GetCurrentTimeTool

# Weather Tools
from .weather_tools import GetWeatherTool, GetForecastTool

# Calculator Tools
from .calculator_tools import CalculatorTool, UnitConverterTool

# System Tools
from .system_tools import SystemInfoTool, SetTimerTool, RunCommandTool

# Web Tools
from .web_tools import WebSearchTool, FetchUrlTool, TranslateTool

# Smart Home Tools
from .smart_home_tools import SmartLightTool, SmartThermostatTool, SmartSceneTool
from .mi_home_tools import MiDeviceScannerTool, MiLightTool

# Music Tools
from .music_tools import MusicPlayerTool
from .migu_tools import MiguMusicTool

# File Tools
from .file_tools import FileReadTool, FileWriteTool, ListDirTool

# Info Tools (News/Stocks)
from .info_tools import NewsBriefingTool, StockPriceTool

# Email & Calendar Tools
from .email_tools import SendEmailTool, ListEmailsTool
from .calendar_tools import AddCalendarEventTool, ListCalendarEventsTool


def get_all_tools():
    """
    Get instances of all available tools.
    """
    return [
        # Time & Date
        GetCurrentTimeTool(),
        
        # Weather
        GetWeatherTool(),
        GetForecastTool(),
        
        # Calculator & Math
        CalculatorTool(),
        UnitConverterTool(),
        
        # System
        SystemInfoTool(),
        SetTimerTool(),
        RunCommandTool(),
        
        # Web
        WebSearchTool(),
        FetchUrlTool(),
        TranslateTool(),
        
        # Smart Home (Simulated)
        SmartLightTool(),
        SmartThermostatTool(),
        SmartSceneTool(),
        
        # Xiaomi Smart Home (Real)
        MiDeviceScannerTool(),
        MiLightTool(),
        
        # Music (Local & Cloud)
        MusicPlayerTool(),
        MiguMusicTool(),

        # File Operations
        FileReadTool(),
        FileWriteTool(),
        ListDirTool(),

        # News & Stocks
        NewsBriefingTool(),
        StockPriceTool(),

        # Email
        SendEmailTool(),
        ListEmailsTool(),

        # Calendar
        AddCalendarEventTool(),
        ListCalendarEventsTool(),
    ]


__all__ = [
    'BaseTool',
    # Time
    'GetCurrentTimeTool',
    # Weather
    'GetWeatherTool',
    'GetForecastTool',
    # Calculator
    'CalculatorTool',
    'UnitConverterTool',
    # System
    'SystemInfoTool',
    'SetTimerTool',
    'RunCommandTool',
    # Web
    'WebSearchTool',
    'FetchUrlTool',
    'TranslateTool',
    # Smart Home
    'SmartLightTool',
    'SmartThermostatTool',
    'SmartSceneTool',
    # News & Stocks
    'NewsBriefingTool',
    'StockPriceTool',
    # Helper
    'get_all_tools',
]
