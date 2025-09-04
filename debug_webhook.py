#!/usr/bin/env python3
"""
Debug script to understand webhook behavior
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
        return self.data.get(query.get("_id"))

def debug_webhook_disabled():
    """Debug why webhook disabled test is failing"""
    print("🔍 Debugging webhook disabled behavior...")
    
    # Mock MongoDB with webhook disabled
    mock_db = MockMongoDB(webhook_enabled=False, custom_message="")
    
    with patch('changelog_discord.mongo_db', mock_db):
        with patch('changelog_discord.os.environ.get') as mock_env:
            # Mock environment variable to return 'false'
            mock_env.return_value = 'false'
            
            from changelog_discord import changelog_notifier
            
            # Manually check the logic
            webhook_enabled_env = os.environ.get('CHANGELOG_WEBHOOK_ENABLED', 'false').lower() == 'true'
            print(f"webhook_enabled_env: {webhook_enabled_env}")
            
            webhook_enabled_db = False
            if mock_db is not None:
                try:
                    changelog_settings = mock_db.site_settings.find_one({"_id": "changelog"})
                    if changelog_settings:
                        webhook_enabled_db = changelog_settings.get("webhook_enabled", False)
                except Exception as e:
                    print(f"Error checking database for webhook settings: {e}")
            
            print(f"webhook_enabled_db: {webhook_enabled_db}")
            
            # Webhook is enabled if either environment variable or database setting is True
            webhook_enabled = webhook_enabled_env or webhook_enabled_db
            print(f"webhook_enabled: {webhook_enabled}")
            
            if not webhook_enabled:
                print("✅ Webhook should be disabled")
            else:
                print("❌ Webhook should be disabled but is enabled")

if __name__ == "__main__":
    debug_webhook_disabled()