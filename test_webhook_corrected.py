#!/usr/bin/env python3
"""
Corrected test for webhook custom message functionality
"""

import os
import sys
from unittest.mock import patch, MagicMock

# Mock MongoDB and requests for testing
class MockMongoDB:
    def __init__(self, webhook_enabled=True, custom_message="🚨 IMPORTANT UPDATE 🚨"):
        self.site_settings = MockCollection(webhook_enabled, custom_message)

class MockCollection:
    def __init__(self, webhook_enabled=True, custom_message="🚨 IMPORTANT UPDATE 🚨"):
        self.data = {
            "changelog": {
                "_id": "changelog",
                "webhook_enabled": webhook_enabled,
                "custom_message": custom_message,
                "message_count": 5
            }
        }
    
    def find_one(self, query):
        # Print for debugging
        # print(f"Mock find_one called with query: {query}")
        return self.data.get(query.get("_id"))

def test_webhook_working():
    """Test that webhook sends messages correctly with custom message"""
    print("🚀 Testing webhook with custom message...")
    
    # Mock the MongoDB with webhook enabled
    mock_db = MockMongoDB(webhook_enabled=True, custom_message="🚨 IMPORTANT UPDATE 🚨")
    
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
                    
                    # Verify the custom message is included
                    expected_content = "🚨 IMPORTANT UPDATE 🚨\n\nTest level has been placed on #1"
                    if sent_content == expected_content:
                        print("✅ Custom message correctly prepended to the main message")
                    else:
                        print(f"❌ Custom message not properly formatted. Expected: {repr(expected_content)}, Got: {repr(sent_content)}")
                        return False
                        
                    if result:
                        print("✅ notify_changelog returned True (success)")
                    else:
                        print("❌ notify_changelog returned False (failure)")
                        return False
                else:
                    print("❌ Webhook was not called")
                    return False
    
    print("🎉 Webhook test with custom message completed successfully!")
    return True

def test_webhook_disabled():
    """Test that webhook doesn't send when disabled"""
    print("\n🔍 Testing webhook disabled functionality...")
    
    # Mock MongoDB with webhook disabled
    mock_db = MockMongoDB(webhook_enabled=False, custom_message="🚨 IMPORTANT UPDATE 🚨")
    
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

def test_no_custom_message():
    """Test webhook with no custom message set"""
    print("\n🔍 Testing webhook with no custom message...")
    
    # Mock MongoDB with no custom message
    mock_db = MockMongoDB(webhook_enabled=True, custom_message="")
    
    with patch('changelog_discord.mongo_db', mock_db):
        with patch('changelog_discord.os.environ.get', return_value='false'):  # No env override
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
                        print(f"❌ Unexpected message content: {repr(sent_content)}")
                        return False
                else:
                    print("❌ Webhook was not called")
                    return False
    
    return True

def test_environment_variable_override():
    """Test that environment variable can override database setting"""
    print("\n🔍 Testing environment variable override...")
    
    # Mock MongoDB with webhook disabled in database
    mock_db = MockMongoDB(webhook_enabled=False, custom_message="🚨 IMPORTANT UPDATE 🚨")  # Disabled in DB
    
    with patch('changelog_discord.mongo_db', mock_db):
        # Mock environment variable to enable webhook
        with patch('changelog_discord.os.environ.get') as mock_env:
            mock_env.side_effect = lambda key, default: 'true' if key == 'CHANGELOG_WEBHOOK_ENABLED' else default
            
            from changelog_discord import notify_changelog
            
            with patch('changelog_discord.requests.post') as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 204
                mock_post.return_value = mock_response
                
                result = notify_changelog("Test message with env override", "TestAdmin")
                
                if mock_post.called:
                    print("✅ Webhook called due to environment variable override")
                else:
                    print("❌ Webhook was not called despite environment variable override")
                    return False
                    
                if result:
                    print("✅ Function returned True with environment variable override")
                else:
                    print("❌ Function should return True with environment variable override")
                    return False
    
    return True

if __name__ == "__main__":
    print("🧪 Webhook Custom Message Corrected Tests\n")
    
    success = True
    success &= test_webhook_working()
    success &= test_webhook_disabled()
    success &= test_no_custom_message()
    success &= test_environment_variable_override()
    
    if success:
        print("\n🎉 All corrected tests passed!")
        print("\n🚀 Your webhook custom message functionality is now working correctly!")
        print("\n📝 To use this feature:")
        print("1. Go to Admin Panel → Webhook Settings")
        print("2. Set your custom message in the 'Custom Message' section")
        print("3. Enable the webhook")
        print("4. All future changelog notifications will include your custom message!")
        print("\n💡 Pro tip: You can also enable the webhook via the CHANGELOG_WEBHOOK_ENABLED environment variable")
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
        sys.exit(1)