#!/usr/bin/env python3
"""
Simple test script for changelog settings
"""

import os

# Set test environment variables
os.environ['CHANGELOG_PING_ENABLED'] = 'true'
os.environ['CHANGELOG_ROLE_ID'] = '1388326130183966720'

try:
    # Test the changelog notification with settings
    from changelog_discord import notify_changelog
    
    print("🧪 Testing changelog settings...")
    
    # Test notification with current settings
    print(f"Current ping enabled setting: {os.environ.get('CHANGELOG_PING_ENABLED', 'Not set')}")
    print(f"Current role ID setting: {os.environ.get('CHANGELOG_ROLE_ID', 'Not set')}")
    
    # Send a test message
    result = notify_changelog("Test notification: Simple settings test message")
    
    if result:
        print("✅ Changelog notification sent successfully!")
    else:
        print("❌ Failed to send changelog notification")
        
except Exception as e:
    print(f"❌ Error testing changelog settings: {e}")
    import traceback
    traceback.print_exc()