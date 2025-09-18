#!/usr/bin/env python3
"""
Test script for changelog functionality on Render
"""

import os
import sys

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set environment variables for Render testing
os.environ['RENDER'] = 'true'
os.environ['CHANGELOG_WEBHOOK_ENABLED'] = 'true'
os.environ['CHANGELOG_WEBHOOK_URL'] = 'https://discord.com/api/webhooks/1412683830539714632/KiH21Ciq1Qpz6im9ZxZ5VC2MXcfjVI18hHwLtY5ooDvygnJ3au9ofXHUzODHewqv9QVw'

try:
    # Test the changelog notification
    from changelog_discord import notify_changelog
    import main  # This will initialize the app and load settings
    
    print("🧪 Testing changelog settings on Render...")
    
    # Test notification with current settings
    print(f"Current RENDER environment: {os.environ.get('RENDER', 'Not set')}")
    print(f"Current CHANGELOG_WEBHOOK_ENABLED setting: {os.environ.get('CHANGELOG_WEBHOOK_ENABLED', 'Not set')}")
    print(f"Current CHANGELOG_WEBHOOK_URL setting: {os.environ.get('CHANGELOG_WEBHOOK_URL', 'Not set')}")
    
    # Send a test message
    result = notify_changelog("Test notification: Changelog system working on Render!")
    
    if result:
        print("✅ Changelog notification sent successfully!")
    else:
        print("❌ Failed to send changelog notification")
        
except Exception as e:
    print(f"❌ Error testing changelog settings: {e}")
    import traceback
    traceback.print_exc()