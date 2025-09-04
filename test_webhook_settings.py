#!/usr/bin/env python3
"""
Test script for webhook settings
"""

import os
import sys

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set test environment variables
os.environ['CHANGELOG_PING_ENABLED'] = 'true'
os.environ['CHANGELOG_ROLE_ID'] = '1388326130183966720'

try:
    # Test the webhook settings
    from changelog_discord import notify_changelog
    
    print("🧪 Testing webhook settings...")
    
    # Test notification with admin name
    result = notify_changelog("Test notification: Webhook settings test", "TestAdmin")
    
    if result:
        print("✅ Webhook notification sent successfully!")
    else:
        print("❌ Failed to send webhook notification")
        
except Exception as e:
    print(f"❌ Error testing webhook settings: {e}")
    import traceback
    traceback.print_exc()