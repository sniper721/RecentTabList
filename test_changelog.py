#!/usr/bin/env python3
"""
Test script for changelog Discord notifications
"""

import os
import sys

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Test the changelog notification
try:
    from changelog_discord import notify_changelog
    
    # Send a test message
    result = notify_changelog("Test notification: Level 'Test Level' has been placed on #1 dethroning 'Previous Level'.")
    
    if result:
        print("✅ Changelog notification sent successfully!")
    else:
        print("❌ Failed to send changelog notification")
        
except Exception as e:
    print(f"❌ Error testing changelog notification: {e}")
    import traceback
    traceback.print_exc()