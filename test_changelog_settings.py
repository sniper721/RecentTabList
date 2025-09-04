#!/usr/bin/env python3
"""
Test script for changelog settings
"""

import os
import sys

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    # Test the changelog notification with settings
    from changelog_discord import notify_changelog
    import main  # This will initialize the app and load settings
    
    print("🧪 Testing changelog settings...")
    
    # Test notification with current settings
    print(f"Current ping enabled setting: {os.environ.get('CHANGELOG_PING_ENABLED', 'Not set')}")
    print(f"Current role ID setting: {os.environ.get('CHANGELOG_ROLE_ID', 'Not set')}")
    
    # Send a test message
    result = notify_changelog("Test notification: Settings test message")
    
    if result:
        print("✅ Changelog notification sent successfully!")
    else:
        print("❌ Failed to send changelog notification")
        
except Exception as e:
    print(f"❌ Error testing changelog settings: {e}")
    import traceback
    traceback.print_exc()