#!/usr/bin/env python3
"""
Test the webhook admin settings to ensure they work properly
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_webhook_admin_settings():
    """Test that the webhook admin settings can be accessed and work"""
    print("🧪 Testing webhook admin settings...")
    
    try:
        # Import main app components
        from main import mongo_db
        
        # Test getting current settings
        changelog_settings = mongo_db.site_settings.find_one({"_id": "changelog"})
        
        if changelog_settings:
            print(f"✅ Current webhook settings found:")
            print(f"   • Webhook enabled: {changelog_settings.get('webhook_enabled', False)}")
            print(f"   • Message format: {changelog_settings.get('message_format', 'detailed')}")
            print(f"   • Include timestamp: {changelog_settings.get('include_timestamp', True)}")
        else:
            print("⚠️  No webhook settings found in database - will use defaults")
        
        # Test updating settings
        test_settings = {
            "_id": "changelog",
            "webhook_enabled": True,
            "ping_enabled": False,
            "ping_threshold": 1,
            "role_id": "1388326130183966720",
            "message_format": "detailed",
            "include_timestamp": True,
            "include_admin": True,
            "color_mode": "default",
            "rate_limit": 10,
            "log_level": "info",
            "message_count": 0
        }
        
        # Update the settings
        result = mongo_db.site_settings.update_one(
            {"_id": "changelog"},
            {"$set": test_settings},
            upsert=True
        )
        
        if result.acknowledged:
            print("✅ Webhook settings updated successfully")
            
            # Verify the update
            updated_settings = mongo_db.site_settings.find_one({"_id": "changelog"})
            if updated_settings and updated_settings.get("webhook_enabled") == True:
                print("✅ Settings verification passed")
                return True
            else:
                print("❌ Settings verification failed")
                return False
        else:
            print("❌ Failed to update webhook settings")
            return False
            
    except Exception as e:
        print(f"❌ Error testing webhook admin settings: {e}")
        return False

def test_webhook_message_sending():
    """Test sending a webhook message through the system"""
    print("\n🧪 Testing webhook message sending...")
    
    try:
        from changelog_discord import notify_changelog
        
        # Send a test message
        result = notify_changelog("🧪 Test message from admin settings test", "TestAdmin")
        
        if result:
            print("✅ Test message sent successfully!")
            return True
        else:
            print("❌ Failed to send test message")
            return False
            
    except Exception as e:
        print(f"❌ Error testing webhook message sending: {e}")
        return False

def main():
    """Run webhook admin tests"""
    print("🚀 Testing Webhook Admin Functionality\n")
    
    tests = [
        test_webhook_admin_settings,
        test_webhook_message_sending
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Webhook admin functionality is working correctly!")
        return True
    else:
        print("❌ Some webhook admin tests failed.")
        return False

if __name__ == "__main__":
    main()