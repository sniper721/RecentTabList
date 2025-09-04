#!/usr/bin/env python3
"""
End-to-end test for webhook custom message functionality
"""

import os
import sys
import json
from unittest.mock import patch, MagicMock

# Mock MongoDB and requests for testing
class MockMongoDB:
    def __init__(self):
        self.site_settings = MockCollection()

class MockCollection:
    def __init__(self):
        self.data = {
            "changelog": {
                "_id": "changelog",
                "webhook_enabled": True,
                "custom_message": "🚨 IMPORTANT UPDATE 🚨",
                "message_count": 5
            }
        }
    
    def find_one(self, query):
        return self.data.get(query.get("_id"))

def test_webhook_end_to_end():
    """Test the complete webhook flow with custom messages"""
    print("🚀 Starting end-to-end webhook test...")
    
    # Mock the MongoDB
    mock_db = MockMongoDB()
    
    # Test the changelog notifier with mocked database
    with patch('changelog_discord.mongo_db', mock_db):
        # Import after patching
        from changelog_discord import notify_changelog
        
        # Capture the message that would be sent
        sent_messages = []
        
        # Mock the requests.post function to capture what would be sent
        with patch('changelog_discord.requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 204
            mock_post.return_value = mock_response
            
            # Test sending a changelog message
            result = notify_changelog("Test level has been placed on #1", "TestAdmin")
            
            # Check if the request was made
            if mock_post.called:
                # Get the arguments that were passed to requests.post
                args, kwargs = mock_post.call_args
                payload = kwargs.get('json', {})
                sent_content = payload.get('content', '')
                
                print(f"✅ Webhook called successfully")
                print(f"📤 Message that would be sent: {sent_content}")
                
                # Verify the custom message is included
                if "🚨 IMPORTANT UPDATE 🚨" in sent_content and "Test level has been placed on #1" in sent_content:
                    print("✅ Custom message correctly prepended to the main message")
                else:
                    print("❌ Custom message not properly included")
                    return False
                    
                if result:
                    print("✅ notify_changelog returned True (success)")
                else:
                    print("❌ notify_changelog returned False (failure)")
                    return False
            else:
                print("❌ Webhook was not called")
                return False
    
    print("🎉 End-to-end webhook test completed successfully!")
    print("\n📝 What this test demonstrates:")
    print("1. Custom messages are retrieved from the database")
    print("2. Custom messages are properly prepended to the main message")
    print("3. The webhook is called with the combined message")
    print("4. The function returns success status correctly")
    return True

def test_webhook_disabled():
    """Test that webhook doesn't send when disabled"""
    print("\n🔍 Testing webhook disabled functionality...")
    
    # Mock MongoDB with webhook disabled
    mock_db = MockMongoDB()
    mock_db.site_settings.data["changelog"]["webhook_enabled"] = False
    
    with patch('changelog_discord.mongo_db', mock_db):
        from changelog_discord import notify_changelog
        
        with patch('changelog_discord.requests.post') as mock_post:
            result = notify_changelog("Test message", "TestAdmin")
            
            if not mock_post.called:
                print("✅ Webhook correctly skipped when disabled")
            else:
                print("❌ Webhook was called despite being disabled")
                return False
                
            if not result:
                print("✅ Function correctly returned False when webhook is disabled")
            else:
                print("❌ Function should return False when webhook is disabled")
                return False
    
    return True

def test_no_custom_message():
    """Test webhook with no custom message set"""
    print("\n🔍 Testing webhook with no custom message...")
    
    # Mock MongoDB with no custom message
    mock_db = MockMongoDB()
    mock_db.site_settings.data["changelog"]["custom_message"] = ""
    mock_db.site_settings.data["changelog"]["webhook_enabled"] = True
    
    with patch('changelog_discord.mongo_db', mock_db):
        from changelog_discord import notify_changelog
        
        with patch('changelog_discord.requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 204
            mock_post.return_value = mock_response
            
            result = notify_changelog("Test message without custom", "TestAdmin")
            
            if mock_post.called:
                args, kwargs = mock_post.call_args
                payload = kwargs.get('json', {})
                sent_content = payload.get('content', '')
                
                if sent_content == "Test message without custom":
                    print("✅ Message sent correctly without custom message")
                else:
                    print(f"❌ Unexpected message content: {sent_content}")
                    return False
            else:
                print("❌ Webhook was not called")
                return False
    
    return True

if __name__ == "__main__":
    print("🧪 Webhook Custom Message End-to-End Tests\n")
    
    success = True
    success &= test_webhook_end_to_end()
    success &= test_webhook_disabled()
    success &= test_no_custom_message()
    
    if success:
        print("\n🎉 All end-to-end tests passed!")
        print("\n🚀 Your webhook custom message functionality is now working correctly!")
        print("\n📝 To use this feature:")
        print("1. Go to Admin Panel → Webhook Settings")
        print("2. Set your custom message in the 'Custom Message' section")
        print("3. Enable the webhook")
        print("4. All future changelog notifications will include your custom message!")
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
        sys.exit(1)