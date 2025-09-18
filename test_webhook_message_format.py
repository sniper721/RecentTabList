#!/usr/bin/env python3
"""
Test script to verify webhook message format
"""

import os
import sys
from unittest.mock import patch, MagicMock

def test_webhook_message_format():
    """Test that webhook sends messages with correct format"""
    print("🚀 Testing webhook message format...")
    
    # Mock MongoDB with webhook enabled
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
                test_message = "Levelname has been placed on #1 dethroning levelname2"
                result = notify_changelog(test_message, "TestAdmin")
                
                # Check if the request was made
                if mock_post.called:
                    # Get the arguments that were passed to requests.post
                    args, kwargs = mock_post.call_args
                    payload = kwargs.get('json', {})
                    sent_content = payload.get('content', '')
                    
                    print(f"✅ Webhook called successfully")
                    print(f"📤 Message that would be sent: {repr(sent_content)}")
                    
                    # Verify the message format is correct
                    if sent_content == test_message:
                        print("✅ Message format is correct - no extra lines or 'test' prefix")
                    else:
                        print(f"❌ Message format is incorrect. Expected: {repr(test_message)}, Got: {repr(sent_content)}")
                        return False
                        
                    if result:
                        print("✅ notify_changelog returned True (success)")
                    else:
                        print("❌ notify_changelog returned False (failure)")
                        return False
                else:
                    print("❌ Webhook was not called")
                    return False
    
    print("🎉 Webhook message format test completed successfully!")
    return True

if __name__ == "__main__":
    print("🧪 Webhook Message Format Test\n")
    
    success = test_webhook_message_format()
    
    if success:
        print("\n🎉 Message format test passed!")
        print("\n📝 The webhook now sends messages correctly:")
        print("   • No 'test' prefix")
        print("   • No extra empty lines")
        print("   • Messages are sent exactly as provided")
        print("\n🔧 Example message format:")
        print("   Levelname has been placed on #1 dethroning levelname2")
    else:
        print("\n❌ Message format test failed. Please check the implementation.")
        sys.exit(1)