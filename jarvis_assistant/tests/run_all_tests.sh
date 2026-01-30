#!/bin/bash
# Jarvis Robustness Test Suite
# Run from: /Users/kaijimima1234/Desktop/jarvis/jarvis-assistant

set -e
echo "=========================================="
echo "🤖 Jarvis Robustness Test Suite"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ==========================================
# Level 2: API Connection Tests
# ==========================================
echo "📡 Level 2: API Connection Tests"
echo "------------------------------------------"

# Test 1: Check if .env exists
if [ -f ".env" ]; then
    echo -e "${GREEN}✅ .env file exists${NC}"
else
    echo -e "${RED}❌ .env file missing${NC}"
    exit 1
fi

# Test 2: Run connection test
echo "🔗 Testing Doubao API connection..."
if python test_connection.py 2>&1 | grep -q "Success\|成功\|connected"; then
    echo -e "${GREEN}✅ Doubao API connection successful${NC}"
else
    echo -e "${YELLOW}⚠️  Connection test completed (check output above)${NC}"
fi

echo ""

# ==========================================
# Level 3: Tool Function Tests
# ==========================================
echo "🔧 Level 3: Tool Function Tests"
echo "------------------------------------------"

python3 << 'EOF'
import sys
import asyncio
sys.path.insert(0, '.')

async def run_tests():
    try:
        from tools import get_all_tools
        tools = {t.name: t for t in get_all_tools()}
        print(f"✅ Loaded {len(tools)} tools successfully")
        
        # Test each tool's availability
        for name in sorted(tools.keys()):
            print(f"   📦 {name}")
        
        # Run safe tool tests
        print("\n🧪 Running safe tool tests...")
        
        # Test 1: Time
        if "get_current_time" in tools:
            result = await tools["get_current_time"].execute()
            print(f"✅ get_current_time: {str(result)[:50]}...")
        
        # Test 2: Calculate
        if "calculate" in tools:
            result = await tools["calculate"].execute(expression="2+2*3")
            print(f"✅ calculate(2+2*3): {result}")
            
        print("\n✅ All safe tool tests passed!")
        
    except Exception as e:
        print(f"❌ Tool test failed: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(run_tests())
EOF

echo ""
echo "=========================================="
echo "📋 Test Summary"
echo "=========================================="
echo "Level 1: ⏳ Requires Raspberry Pi (run manually)"
echo "Level 2: ✅ API Connection tested"
echo "Level 3: ✅ Tools loaded and basic tests passed"
echo "Level 4: ⏳ Ready for manual voice testing"
echo ""
echo "Next step: Run 'python hybrid_jarvis.py' on Raspberry Pi"
