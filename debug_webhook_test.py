#!/usr/bin/env python3
"""
Debug the actual webhook test
"""

import os
from unittest.mock import patch, MagicMock

# Mock MongoDB
class MockMongoDB:
    def __init__(self, webhook_enabled=False, custom_message=""):
        self.site_settings = MockCollection(webhook_enabled, custom_message)

class MockCollection:
    def __init__(self, webhook_enabled=False, custom_message=""):
        self.data = {
            "changelog": {
                "_id": "changelog",
                "webhook_enabled": webhook_enabled,
                "custom_message": custom_message,
                "message_count": 5
            }
        }
    
    def find_one(self, query):
        print(f"Mock find_one called with query: {query}")
        result = self.data.get(query.get("_id"))
        print(f"Returning: {result}")
        return result

def debug_actual_test():
    """Debug the actual test that's failing"""
    print("🔍 Debugging actual test behavior...")
    
    # Mock MongoDB with webhook disabled
    mock_db = MockMongoDB(webhook_enabled=False, custom_message="")
    
    with patch('changelog_discord.mongo_db', mock_db):
        from changelog_discord import notify_changelog
        
        # Mock requests.post to verify it's NOT called
        with patch('changelog_discord.requests.post') as mock_post:
            print("Calling notify_changelog with disabled webhook...")
            result = notify_changelog("Test message", "TestAdmin")
            print(f"notify_changelog returned: {result}")
            
            # Check that requests.post was NOT called
            if not mock_post.called:
                print("✅ Webhook correctly skipped when disabled")
            else:
                print("❌ Webhook was called despite being disabled")
                # Let's see what was called
                print(f"mock_post.called: {mock_post.called}")
                if mock_post.called:
                    args, kwargs = mock_post.call_args
                    print(f"Called with args: {args}")
                    print(f"Called with kwargs: {kwargs}")

if __name__ == "__main__":
    debug_actual_test()