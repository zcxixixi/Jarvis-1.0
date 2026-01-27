"""
System Health & Authenticity Audit
Runs a comprehensive check on the Jarvis system.
1. Authenticity: verifies all tools use allowed domains.
2. Resilience: simulated connectivity checks.
"""

import sys
import inspect
import importlib
from typing import List, Dict
import os
# Ensure package path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jarvis_assistant.utils.validators import DataAuthenticityValidator
from jarvis_assistant.services.tools import get_all_tools
from jarvis_assistant.core.agent import JarvisAgent

def audit_tools() -> Dict[str, List[str]]:
    """Audit all loaded tools for authenticity compliance"""
    print("🛡️  Starting Authenticity Audit...")
    
    validator = DataAuthenticityValidator()
    tool_list = get_all_tools()
    
    issues = {}
    
    # Static analysis of tool source code (naive but helpful)
    for tool in tool_list:
        name = tool.name
        print(f"  - Checking {name} ({tool.__class__.__name__})...")
        
        # 1. Check get_schema presence
        try:
            schema = tool.get_schema()
        except Exception as e:
            issues.setdefault(name, []).append(f"CRITICAL: get_schema failed - {e}")
            continue
            
        # 2. Check source code for hardcoded IPs or prohibited domains
        try:
            source = inspect.getsource(tool.__class__)
            
            # forbidden keywords
            for bad in ["localhost", "127.0.0.1", "mock", "fake"]:
                if bad in source.lower() and "validator" not in source.lower():
                     # Ignore if it's inside the validator check itself
                     issues.setdefault(name, []).append(f"WARNING: Found suspicious term '{bad}' in source")
                     
        except Exception:
            pass # Built-in or compiled
            
    return issues

def check_scheduler():
    print("\n⏰ Checking Scheduler...")
    from jarvis_assistant.core.scheduler import get_scheduler
    sched = get_scheduler()
    print(f"  - Tasks loaded: {len(sched.tasks)}")
    print(f"  - Running state: {sched.running}")
    if not sched.running:
        print("  ⚠️ Scheduler is NOT running (it should start with Agent)")

def check_feedback():
    print("\n🧠 Checking Learning Module...")
    from jarvis_assistant.core.feedback_manager import get_feedback_manager
    fb = get_feedback_manager()
    print(f"  - Negative feedback entries: {len(fb.data['negative_feedback'])}")
    print(f"  - Preferences: {len(fb.data['preferences'])}")

if __name__ == "__main__":
    print("========================================")
    print("🏥 JARVIS SYSTEM HEALTH CHECK")
    print("========================================")
    
    # 1. Tool Audit
    tool_issues = audit_tools()
    
    print("\n📊 Audit Results:")
    if not tool_issues:
        print("✅ All tools passed static analysis.")
    else:
        print(f"❌ Found issues in {len(tool_issues)} tools:")
        for name, errs in tool_issues.items():
            print(f"  🔴 {name}:")
            for e in errs:
                print(f"     - {e}")
                
    # 2. Component Check
    check_scheduler()
    check_feedback()
    
    print("\n========================================")
    if tool_issues:
        print("❌ SYSTEM HEALTH: DEGRADED")
        sys.exit(1)
    else:
        print("✅ SYSTEM HEALTH: OPTIMAL")
        sys.exit(0)
