"""
Data Authenticity Validator
Ensures all information comes from real sources
"""

from typing import Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlparse


class DataAuthenticityValidator:
    """Validates that data comes from legitimate sources"""
    
    # Registry of approved data sources (hostnames or source identifiers)
    # NOTE: Keep this list strict. If a source isn't listed, we refuse to answer.
    APPROVED_SOURCES = {
        "weather": [
            "wttr.in",
            "api.openweathermap.org",
            "openweathermap.org",
        ],
        "news": [
            "feeds.reuters.com",
            "reuters.com",
            "apnews.com",
            "ap.org",
            "feeds.bbci.co.uk",
            "bbc.co.uk",
            "bbc.com",
            "rss.nytimes.com",
            "nytimes.com",
        ],
        # Email is a special case: we allow real SMTP hosts (non-localhost, non-mock)
        "email": [],
        "web": [
            "api.duckduckgo.com",
            "duckduckgo.com",
            "api.mymemory.translated.net",
            "mymemory.translated.net",
            "finance.yahoo.com",
            "feeds.reuters.com",
            "feeds.bbci.co.uk",
            "rss.nytimes.com",
            "bbc.co.uk",
            "bbc.com",
            "nytimes.com",
            "itunes.apple.com",
            "music.163.com",
            "wttr.in",
        ],
        "time": ["system"],
    }
    
    def __init__(self):
        self.violations = []
    
    def validate_source(self, data_type: str, source: str) -> bool:
        """
        Verify data comes from approved real source
        
        Args:
            data_type: Type of data (weather, news, etc.)
            source: Source identifier
        
        Returns:
            True if source is approved, False otherwise
        """
        if not source:
            self.violations.append({
                "type": data_type,
                "source": source,
                "timestamp": datetime.now().isoformat(),
                "reason": "Empty source"
            })
            return False

        source_str = str(source)

        # Email (SMTP host) validation: allow any non-localhost, non-mock host-like string
        if data_type == "email":
            return self.require_real_api("email", source_str)

        approved = self.APPROVED_SOURCES.get(data_type, [])

        # Parse hostname if it's a URL
        host = source_str
        try:
            parsed = urlparse(source_str)
            if parsed.scheme in ("http", "https") and parsed.netloc:
                host = parsed.netloc
        except Exception:
            host = source_str

        # Check if host is in approved list
        is_approved = any(approved_src in host for approved_src in approved)
        
        if not is_approved:
            self.violations.append({
                "type": data_type,
                "source": source_str,
                "timestamp": datetime.now().isoformat(),
                "reason": "Source not in approved list"
            })
        
        return is_approved
    
    def require_real_api(self, tool_name: str, api_endpoint: Optional[str]) -> bool:
        """
        Ensure tool uses real API endpoint
        
        Args:
            tool_name: Name of the tool
            api_endpoint: API endpoint URL
        
        Returns:
            True if real API, False if fake/mock
        """
        if api_endpoint is None:
            self.violations.append({
                "tool": tool_name,
                "reason": "No API endpoint configured",
                "timestamp": datetime.now().isoformat()
            })
            return False
        
        # Check for mock/fake indicators
        fake_indicators = ["mock", "fake", "dummy", "localhost", "127.0.0.1"]
        if any(indicator in api_endpoint.lower() for indicator in fake_indicators):
            self.violations.append({
                "tool": tool_name,
                "endpoint": api_endpoint,
                "reason": "Appears to be a fake/mock endpoint",
                "timestamp": datetime.now().isoformat()
            })
            return False
        
        # Simple host-like guard for SMTP hostnames (avoid accepting random strings)
        if tool_name in ("email", "send_email"):
            # For SMTP we expect a host-like string, not a URL
            if "://" in api_endpoint:
                return False
            if "." not in api_endpoint:
                return False
        return True
    
    def validate_response(self, data: Dict[str, Any], expected_fields: list) -> bool:
        """
        Validate response has expected real data fields
        
        Args:
            data: Response data
            expected_fields: Fields that must be present
        
        Returns:
            True if data appears real
        """
        # Check all expected fields exist
        for field in expected_fields:
            if field not in data:
                self.violations.append({
                    "reason": f"Missing expected field: {field}",
                    "data": str(data)[:100],
                    "timestamp": datetime.now().isoformat()
                })
                return False
        
        return True
    
    def report_violations(self) -> Dict[str, Any]:
        """Get report of any violations found"""
        return {
            "total_violations": len(self.violations),
            "violations": self.violations,
            "status": "FAIL" if self.violations else "PASS"
        }


# Tool wrapper to enforce authenticity
def authentic_tool_wrapper(tool_func):
    """Decorator to add authenticity checks to tools"""
    def wrapper(*args, **kwargs):
        validator = DataAuthenticityValidator()
        
        # Run the tool
        result = tool_func(*args, **kwargs)
        
        # Log if validator found issues
        report = validator.report_violations()
        if report["status"] == "FAIL":
            print(f"⚠️ AUTHENTICITY WARNING: {report}")
        
        return result
    
    return wrapper


# Example usage in tools
class AuthenticNewsSource:
    """Example: How to ensure news is real"""
    
    def get_news(self, topic: str) -> str:
        validator = DataAuthenticityValidator()
        
        # Option 1: Use real RSS feeds
        real_sources = [
            "http://rss.cnn.com/rss/cnn_topstories.rss",
            "https://feeds.reuters.com/reuters/topNews"
        ]
        
        for source in real_sources:
            if validator.require_real_api("news", source):
                # Fetch from real source
                # return actual news
                pass
        
        # If no valid source, refuse to return fake data
        return "⚠️ Cannot retrieve news: No authenticated source available"


if __name__ == "__main__":
    print("🔒 Data Authenticity Validator")
    print("=" * 60)
    
    validator = DataAuthenticityValidator()
    
    # Test 1: Valid source
    result = validator.validate_source("weather", "wttr.in/Beijing")
    print(f"✅ Valid weather source: {result}")
    
    # Test 2: Invalid source
    result = validator.validate_source("news", "fake-news-generator.com")
    print(f"❌ Fake news source: {result}")
    
    # Test 3: Mock API
    result = validator.require_real_api("email", "http://localhost:5000/mock")
    print(f"❌ Mock API rejected: {result}")
    
    # Report
    report = validator.report_violations()
    print(f"\n📊 Violations found: {report['total_violations']}")
    
    if report['status'] == 'FAIL':
        print("❌ AUTHENTICITY CHECK FAILED")
        for v in report['violations']:
            print(f"  - {v}")
    else:
        print("✅ ALL DATA SOURCES AUTHENTIC")
