#!/usr/bin/env python3
"""
Jarvis Skills Test Suite
Tests all tools and measures latency
"""
import asyncio
import time
from datetime import datetime
from typing import Dict, List, Tuple

# Import all tools
from tools import get_all_tools


async def measure_tool_latency(tool, test_args: dict) -> Tuple[str, float, str]:
    """
    Measure execution time for a single tool.
    
    Returns:
        Tuple of (tool_name, latency_ms, result_preview)
    """
    start = time.perf_counter()
    try:
        result = await tool.execute(**test_args)
        latency = (time.perf_counter() - start) * 1000  # Convert to ms
        # Truncate result for preview
        preview = str(result)[:100] + "..." if len(str(result)) > 100 else str(result)
        return (tool.name, latency, preview, "✅ SUCCESS")
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return (tool.name, latency, str(e)[:100], "❌ FAILED")


async def run_all_tests() -> List[dict]:
    """Run tests for all tools and collect results."""
    
    # Define test cases for each tool
    test_cases = {
        "get_current_time": {"format": "full"},
        "get_weather": {"city": "Beijing"},
        "get_forecast": {"city": "Shanghai", "days": 2},
        "calculate": {"expression": "2 + 3 * 4"},
        "convert_unit": {"value": 100, "from_unit": "km", "to_unit": "mile"},
        "get_system_info": {"detail": "all"},
        "set_timer": {"minutes": 5, "message": "测试提醒"},
        "run_command": {"command": "date"},
        "web_search": {"query": "Python programming"},
        "fetch_url": {"url": "https://example.com"},
        "translate": {"text": "Hello world", "to_lang": "zh"},
        "control_light": {"room": "客厅", "action": "status"},
        "control_thermostat": {"action": "status"},
        "activate_scene": {"scene": "home"},
        "scan_xiaomi_devices": {},
        "control_xiaomi_light": {"ip": "192.168.1.100", "token": "mock_token", "action": "on"},
    }
    
    tools = get_all_tools()
    results = []
    
    print("=" * 60)
    print("🧪 JARVIS SKILLS TEST SUITE")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()
    
    for tool in tools:
        args = test_cases.get(tool.name, {})
        print(f"Testing: {tool.name}...", end=" ", flush=True)
        
        name, latency, preview, status = await measure_tool_latency(tool, args)
        
        results.append({
            "name": name,
            "description": tool.description,
            "latency_ms": round(latency, 2),
            "status": status,
            "result_preview": preview
        })
        
        print(f"{status} ({latency:.1f}ms)")
    
    return results


def generate_report(results: List[dict]) -> str:
    """Generate a formatted latency report."""
    
    report = []
    report.append("\n" + "=" * 60)
    report.append("📊 JARVIS SKILLS LATENCY REPORT")
    report.append("=" * 60 + "\n")
    
    # Header
    report.append(f"{'Tool Name':<25} {'Latency':<12} {'Status':<12}")
    report.append("-" * 50)
    
    total_latency = 0
    success_count = 0
    
    for r in results:
        latency_str = f"{r['latency_ms']:.1f}ms"
        status_icon = "✅" if "SUCCESS" in r['status'] else "❌"
        report.append(f"{r['name']:<25} {latency_str:<12} {status_icon}")
        total_latency += r['latency_ms']
        if "SUCCESS" in r['status']:
            success_count += 1
    
    report.append("-" * 50)
    
    # Summary
    avg_latency = total_latency / len(results) if results else 0
    report.append(f"\n📈 Summary:")
    report.append(f"   Total Tools: {len(results)}")
    report.append(f"   Successful: {success_count}/{len(results)}")
    report.append(f"   Average Latency: {avg_latency:.1f}ms")
    report.append(f"   Total Test Time: {total_latency:.1f}ms")
    
    # Categorize by speed
    report.append(f"\n⚡ Speed Categories:")
    fast = [r for r in results if r['latency_ms'] < 10]
    medium = [r for r in results if 10 <= r['latency_ms'] < 100]
    slow = [r for r in results if 100 <= r['latency_ms'] < 1000]
    very_slow = [r for r in results if r['latency_ms'] >= 1000]
    
    if fast:
        report.append(f"   🚀 Fast (<10ms): {', '.join(r['name'] for r in fast)}")
    if medium:
        report.append(f"   ⚡ Medium (10-100ms): {', '.join(r['name'] for r in medium)}")
    if slow:
        report.append(f"   🐢 Slow (100ms-1s): {', '.join(r['name'] for r in slow)}")
    if very_slow:
        report.append(f"   🦥 Very Slow (>1s): {', '.join(r['name'] for r in very_slow)}")
    
    report.append("\n" + "=" * 60)
    
    return "\n".join(report)


def save_detailed_results(results: List[dict], filepath: str):
    """Save detailed results to file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("# Jarvis Skills Test Results\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Latency Summary\n\n")
        f.write("| Tool | Description | Latency | Status |\n")
        f.write("|------|-------------|---------|--------|\n")
        
        for r in results:
            status = "✅" if "SUCCESS" in r['status'] else "❌"
            desc = r['description'][:30] + "..." if len(r['description']) > 30 else r['description']
            f.write(f"| {r['name']} | {desc} | {r['latency_ms']:.1f}ms | {status} |\n")
        
        f.write("\n## Detailed Results\n\n")
        for r in results:
            f.write(f"### {r['name']}\n")
            f.write(f"- **Description**: {r['description']}\n")
            f.write(f"- **Latency**: {r['latency_ms']:.2f}ms\n")
            f.write(f"- **Status**: {r['status']}\n")
            f.write(f"- **Result Preview**: {r['result_preview']}\n\n")


async def main():
    """Main entry point."""
    results = await run_all_tests()
    
    # Generate and print report
    report = generate_report(results)
    print(report)
    
    # Save detailed results
    results_file = "test_results.md"
    save_detailed_results(results, results_file)
    print(f"\n💾 Detailed results saved to: {results_file}")


if __name__ == "__main__":
    asyncio.run(main())
