#!/usr/bin/env python3
"""
Test script to verify the changelog bot fixes:
1. No bold text formatting
2. Webhook settings work properly
3. Only one message is sent per action
"""

import os
import sys
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_no_bold_formatting():
    """Test that messages don't contain bold formatting"""
    print("🧪 Testing: No bold formatting in messages...")
    
    try:
        from changelog_discord import send_changelog_notification
        
        # Test different message types
        test_cases = [
            ("placed", "Test Level", "TestAdmin", {"position": 1, "dethroned_level": "Old Level"}),
            ("moved", "Test Level", "TestAdmin", {"old_position": 5, "new_position": 3}),
            ("removed", "Test Level", "TestAdmin", {"old_position": 10}),
            ("legacy", "Test Level", "TestAdmin", {"old_position": 100, "legacy_position": 1})
        ]
        
        for action, level_name, admin, kwargs in test_cases:
            # Mock the notify_changelog function to capture the message
            with patch('changelog_discord.notify_changelog') as mock_notify:
                mock_notify.return_value = True
                
                result = send_changelog_notification(action, level_name, admin, **kwargs)
                
                if mock_notify.called:
                    message = mock_notify.call_args[0][0]  # First argument is the message
                    
                    # Check for bold formatting
                    if "**" in message:
                        print(f"❌ Bold formatting found in {action} message: {message}")
                        return False
                    else:
                        print(f"✅ No bold formatting in {action} message: {message}")
                else:
                    print(f"❌ notify_changelog was not called for {action}")
                    return False
        
        print("✅ All messages are free of bold formatting!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing bold formatting: {e}")
        return False

def test_single_message_sending():
    """Test that only one message is sent per action"""
    print("\n🧪 Testing: Only one message sent per action...")
    
    try:
        from changelog_discord import notify_changelog
        
        # Mock requests.post to count calls
        with patch('changelog_discord.requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 204
            mock_post.return_value = mock_response
            
            # Test sending a message
            result = notify_changelog("Test message for single send", "TestAdmin")
            
            # Check that requests.post was called exactly once
            if mock_post.call_count == 1:
                print("✅ Only one HTTP request made per message")
                return True
            else:
                print(f"❌ Expected 1 HTTP request, but got {mock_post.call_count}")
                return False
                
    except Exception as e:
        print(f"❌ Error testing single message sending: {e}")
        return False

def test_webhook_settings_functionality():
    """Test that webhook settings work properly"""
    print("\n🧪 Testing: Webhook settings functionality...")
    
    try:
        # Mock database
        mock_db = MagicMock()
        mock_settings = {
            "_id": "changelog",
            "webhook_enabled": True,
            "ping_enabled": False,
            "message_format": "detailed"
        }
        mock_db.site_settings.find_one.return_value = mock_settings
        
        with patch('changelog_discord.mongo_db', mock_db):
            # Mock environment variable to be false so we only test database settings
            with patch('changelog_discord.os.environ.get') as mock_env:
                mock_env.return_value = 'false'  # Environment variable disabled
                
                from changelog_discord import notify_changelog
                
                # Mock requests.post
                with patch('changelog_discord.requests.post') as mock_post:
                    mock_response = MagicMock()
                    mock_response.status_code = 204
                    mock_post.return_value = mock_response
                    
                    # Test with webhook enabled in database
                    result = notify_changelog("Test webhook settings", "TestAdmin")
                    
                    if result and mock_post.called:
                        print("✅ Webhook settings work correctly when enabled")
                        
                        # Test with webhook disabled in database
                        mock_settings["webhook_enabled"] = False
                        mock_post.reset_mock()
                        
                        result = notify_changelog("Test webhook disabled", "TestAdmin")
                        
                        if not result and not mock_post.called:
                            print("✅ Webhook correctly disabled when settings are off")
                            return True
                        else:
                            print("❌ Webhook not properly disabled")
                            return False
                    else:
                        print("❌ Webhook not working when enabled")
                        return False
                    
    except Exception as e:
        print(f"❌ Error testing webhook settings: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing Changelog Bot Fixes\n")
    
    tests = [
        test_no_bold_formatting,
        test_single_message_sending,
        test_webhook_settings_functionality
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()  # Add spacing between tests
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The changelog bot fixes are working correctly.")
        print("\n✅ Summary of fixes:")
        print("   • Removed bold text formatting from all messages")
        print("   • Fixed webhook settings to work properly")
        print("   • Ensured only one message is sent per action")
        print("   • Removed duplicate function calls")
        return True
    else:
        print("❌ Some tests failed. Please check the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)