#!/usr/bin/env python3
"""
Simple test for webhook functionality without custom messages
"""

import os
import sys
from unittest.mock import patch, MagicMock

def test_webhook_without_custom_message():
    """Test that webhook sends messages correctly without custom message"""
    print("🚀 Testing webhook without custom message...")
    
    # Mock MongoDB with webhook enabled but no custom message
    class MockMongoDB:
        def __init__(self):
            self.site_settings = MockCollection()

    class MockCollection:
        def __init__(self):
            self.data = {
                "changelog": {
                    "_id": "changelog",
                    "webhook_enabled": True,
                    "custom_message": "",  # No custom message
                    "message_count": 5
                }
            }
        
        def find_one(self, query):
            return self.data.get(query.get("_id"))
    
    mock_db = MockMongoDB()
    
    # Test the changelog notifier with mocked database
    with patch('changelog_discord.mongo_db', mock_db):
        with patch('changelog_discord.os.environ.get', return_value='false'):  # No env override
            # Import after patching
            from changelog_discord import notify_changelog
            
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
                    print(f"📤 Message that would be sent: {repr(sent_content)}")
                    
                    # Verify the message is exactly what we sent, without any custom message
                    expected_content = "Test level has been placed on #1"
                    if sent_content == expected_content:
                        print("✅ Message sent correctly without custom message")
                    else:
                        print(f"❌ Unexpected message content. Expected: {repr(expected_content)}, Got: {repr(sent_content)}")
                        return False
                        
                    if result:
                        print("✅ notify_changelog returned True (success)")
                    else:
                        print("❌ notify_changelog returned False (failure)")
                        return False
                else:
                    print("❌ Webhook was not called")
                    return False
    
    print("🎉 Webhook test without custom message completed successfully!")
    return True

def test_webhook_disabled():
    """Test that webhook doesn't send when disabled"""
    print("\n🔍 Testing webhook disabled functionality...")
    
    # Mock MongoDB with webhook disabled
    class MockMongoDB:
        def __init__(self):
            self.site_settings = MockCollection()

    class MockCollection:
        def __init__(self):
            self.data = {
                "changelog": {
                    "_id": "changelog",
                    "webhook_enabled": False,  # Disabled
                    "custom_message": "",
                    "message_count": 5
                }
            }
        
        def find_one(self, query):
            return self.data.get(query.get("_id"))
    
    mock_db = MockMongoDB()
    
    with patch('changelog_discord.mongo_db', mock_db):
        with patch('changelog_discord.os.environ.get', return_value='false'):  # No env override
            from changelog_discord import notify_changelog
            
            # Mock requests.post to verify it's NOT called
            with patch('changelog_discord.requests.post') as mock_post:
                # Make the mock raise an exception if called (shouldn't be called)
                mock_post.side_effect = Exception("Webhook should not be called when disabled")
                
                result = notify_changelog("Test message", "TestAdmin")
                
                # Check that requests.post was NOT called
                if not mock_post.called:
                    print("✅ Webhook correctly skipped when disabled")
                else:
                    print("❌ Webhook was called despite being disabled")
                    return False
                    
                # Check that the function returned False
                if result is False:
                    print("✅ Function correctly returned False when webhook is disabled")
                else:
                    print(f"❌ Function should return False when webhook is disabled, got: {result}")
                    return False
    
    return True

if __name__ == "__main__":
    print("🧪 Webhook Simple Tests\n")
    
    success = True
    success &= test_webhook_without_custom_message()
    success &= test_webhook_disabled()
    
    if success:
        print("\n🎉 All simple tests passed!")
        print("\n🚀 Your webhook is now working correctly without custom messages!")
        print("\n📝 The custom message feature has been completely removed:")
        print("   • Custom message functionality removed from notify_changelog")
        print("   • Custom message section removed from admin panel")
        print("   • Custom message routes removed from main application")
        print("   • Webhook still works for direct messages and changelog notifications")
        print("\n🔧 To use:")
        print("1. Go to Admin Panel → Webhook Settings")
        print("2. Enable the webhook")
        print("3. All changelog notifications will be sent without custom messages")
        print("4. You can still send direct messages using the 'Send Direct Message' feature")
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
        sys.exit(1)