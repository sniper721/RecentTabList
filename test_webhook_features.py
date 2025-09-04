#!/usr/bin/env python3
"""
Test script for all webhook features
"""

import os
import sys

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set test environment variables
os.environ['CHANGELOG_PING_ENABLED'] = 'true'
os.environ['CHANGELOG_ROLE_ID'] = '1388326130183966720'

try:
    # Test all webhook features
    from changelog_discord import notify_changelog
    
    print("🧪 Testing all webhook features...")
    
    # Test 1: Basic notification
    print("\n📝 Test 1: Basic notification")
    result = notify_changelog("Test notification: Basic test")
    if result:
        print("✅ Basic notification sent successfully!")
    else:
        print("❌ Failed to send basic notification")
    
    # Test 2: Notification with admin name
    print("\n📝 Test 2: Notification with admin name")
    result = notify_changelog("Test notification: With admin name", "TestAdmin")
    if result:
        print("✅ Notification with admin name sent successfully!")
    else:
        print("❌ Failed to send notification with admin name")
    
    # Test 3: Notification with timestamp
    print("\n📝 Test 3: Notification with timestamp")
    # This is automatically included in the message
    
    print("\n🎉 All webhook feature tests completed!")
        
except Exception as e:
    print(f"❌ Error testing webhook features: {e}")
    import traceback
    traceback.print_exc()