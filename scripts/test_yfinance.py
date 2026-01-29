import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from jarvis_assistant.services.tools import info_tools

async def test_stock():
    print("Testing Stock Tool...")
    # Test with "Apple" which maps to AAPL
    result = await info_tools.get_stock_price("苹果")
    print(f"Result (苹果): {result}")
    
    # Test with direct symbol
    result = await info_tools.get_stock_price("AAPL")
    print(f"Result (AAPL): {result}")

if __name__ == "__main__":
    asyncio.run(test_stock())
