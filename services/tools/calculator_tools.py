"""
Calculator Tools
Provides mathematical calculation and unit conversion
"""
import math
from typing import Dict, Any
from .base import BaseTool


class CalculatorTool(BaseTool):
    """Perform mathematical calculations"""
    
    @property
    def name(self) -> str:
        return "calculate"
    
    @property
    def description(self) -> str:
        return "执行数学计算，支持基础运算、三角函数、对数等"
    
    def get_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "数学表达式，例如：'2+3*4', 'sqrt(16)', 'sin(30)'"
                        }
                    },
                    "required": ["expression"]
                }
            }
        }
    
    async def execute(self, **kwargs) -> str:
        """Safely evaluate mathematical expression"""
        expression = kwargs.get("expression")
        if not expression:
            return "❌ 错误：未提供数学表达式"
        try:
            # Define safe math functions
            safe_dict = {
                "sin": lambda x: math.sin(math.radians(x)),
                "cos": lambda x: math.cos(math.radians(x)),
                "tan": lambda x: math.tan(math.radians(x)),
                "sqrt": math.sqrt,
                "log": math.log10,
                "ln": math.log,
                "exp": math.exp,
                "pow": pow,
                "abs": abs,
                "pi": math.pi,
                "e": math.e,
                "floor": math.floor,
                "ceil": math.ceil,
                "round": round,
            }
            
            # Clean expression
            expr = expression.replace("^", "**").replace("×", "*").replace("÷", "/")
            
            # Evaluate safely
            result = eval(expr, {"__builtins__": {}}, safe_dict)
            
            # Format result
            if isinstance(result, float):
                if result == int(result):
                    return f"🔢 {expression} = {int(result)}"
                else:
                    return f"🔢 {expression} = {result:.6g}"
            return f"🔢 {expression} = {result}"
            
        except ZeroDivisionError:
            return "❌ 错误：除数不能为零"
        except Exception as e:
            return f"❌ 计算错误：{str(e)}"


class UnitConverterTool(BaseTool):
    """Convert between different units"""
    
    @property
    def name(self) -> str:
        return "convert_unit"
    
    @property
    def description(self) -> str:
        return "单位换算：长度、重量、温度、面积等"
    
    def get_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "value": {
                            "type": "number",
                            "description": "要换算的数值"
                        },
                        "from_unit": {
                            "type": "string",
                            "description": "原单位：km, m, cm, mm, mile, ft, inch, kg, g, lb, oz, celsius, fahrenheit, kelvin, sqm, sqft, hectare, acre"
                        },
                        "to_unit": {
                            "type": "string",
                            "description": "目标单位"
                        }
                    },
                    "required": ["value", "from_unit", "to_unit"]
                }
            }
        }
    
    async def execute(self, **kwargs) -> str:
        """Convert between units"""
        value = kwargs.get("value")
        from_unit = str(kwargs.get("from_unit", "")).lower().strip()
        to_unit = str(kwargs.get("to_unit", "")).lower().strip()
        
        if value is None or not from_unit or not to_unit:
            return "❌ 错误：参数不完整"
            
        # Length conversions to meters
        length_to_m = {
            "km": 1000, "m": 1, "cm": 0.01, "mm": 0.001,
            "mile": 1609.344, "ft": 0.3048, "inch": 0.0254, "yard": 0.9144
        }
        
        # Weight conversions to kg
        weight_to_kg = {
            "kg": 1, "g": 0.001, "mg": 0.000001,
            "lb": 0.453592, "oz": 0.0283495, "ton": 1000
        }
        
        # Area conversions to sqm
        area_to_sqm = {
            "sqm": 1, "sqft": 0.092903, "sqkm": 1000000,
            "hectare": 10000, "acre": 4046.86
        }
        
        try:
            # Temperature (special handling)
            if from_unit in ["celsius", "c", "摄氏度"] or to_unit in ["celsius", "c", "摄氏度"]:
                if from_unit in ["fahrenheit", "f", "华氏度"]:
                    result = (value - 32) * 5 / 9
                elif from_unit in ["kelvin", "k", "开尔文"]:
                    result = value - 273.15
                elif to_unit in ["fahrenheit", "f", "华氏度"]:
                    result = value * 9 / 5 + 32
                elif to_unit in ["kelvin", "k", "开尔文"]:
                    result = value + 273.15
                else:
                    result = value
                return f"📏 {value} {from_unit} = {result:.2f} {to_unit}"
            
            # Length
            if from_unit in length_to_m and to_unit in length_to_m:
                result = value * length_to_m[from_unit] / length_to_m[to_unit]
                return f"📏 {value} {from_unit} = {result:.4g} {to_unit}"
            
            # Weight
            if from_unit in weight_to_kg and to_unit in weight_to_kg:
                result = value * weight_to_kg[from_unit] / weight_to_kg[to_unit]
                return f"⚖️ {value} {from_unit} = {result:.4g} {to_unit}"
            
            # Area
            if from_unit in area_to_sqm and to_unit in area_to_sqm:
                result = value * area_to_sqm[from_unit] / area_to_sqm[to_unit]
                return f"📐 {value} {from_unit} = {result:.4g} {to_unit}"
            
            return f"❌ 不支持的单位换算：{from_unit} -> {to_unit}"
            
        except Exception as e:
            return f"❌ 换算错误：{str(e)}"
