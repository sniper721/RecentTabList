#!/usr/bin/env python3
"""
Test Discord webhook functionality
"""

import os
from dotenv import load_dotenv
from discord_integration import notify_record_approved, notify_record_rejected

load_dotenv()

def test_webhook():
    print("🧪 Testing Discord Webhook Integration")
    print("=" * 50)
    
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        print("❌ No webhook URL configured")
        return False
    
    print(f"✅ Webhook URL configured: {webhook_url[:50]}...")
    
    # Test record approval notification
    print("\n📝 Testing record approval notification...")
    try:
        notify_record_approved("TestUser", "Test Level", 100, 50)
        print("✅ Record approval notification sent")
    except Exception as e:
        print(f"❌ Record approval failed: {e}")
    
    # Test record rejection notification
    print("\n📝 Testing record rejection notification...")
    try:
        notify_record_rejected("TestUser", "Test Level", 75, "Test rejection reason")
        print("✅ Record rejection notification sent")
    except Exception as e:
        print(f"❌ Record rejection failed: {e}")
    
    print("\n🎯 Webhook test completed!")
    return True

if __name__ == "__main__":
    test_webhook()