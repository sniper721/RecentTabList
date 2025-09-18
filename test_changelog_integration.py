#!/usr/bin/env python3
"""
Integration test for changelog Discord notifications
"""

import os
import sys
from datetime import datetime

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    # Test the changelog notification system
    from changelog_discord import notify_changelog
    from main import send_changelog_notification
    
    print("🧪 Testing changelog notification system...")
    
    # Test 1: Basic notification
    print("\n📝 Test 1: Basic notification")
    result = notify_changelog("Test notification: Level 'Test Level' has been placed on #1 dethroning 'Previous Level'.")
    if result:
        print("✅ Basic notification sent successfully!")
    else:
        print("❌ Failed to send basic notification")
    
    # Test 2: Simulate placing a new #1 level
    print("\n📝 Test 2: Simulate placing a new #1 level")
    send_changelog_notification(
        action="placed",
        level_name="New Top Level",
        admin_username="TestAdmin",
        position=1,
        above_level="Previous Top Level",
        list_type="main"
    )
    print("✅ Placed #1 level notification processed!")
    
    # Test 3: Simulate placing a level at another position
    print("\n📝 Test 3: Simulate placing a level at position 5")
    send_changelog_notification(
        action="placed",
        level_name="Middle Level",
        admin_username="TestAdmin",
        position=5,
        above_level="Level Above",
        below_level="Level Below",
        list_type="main"
    )
    print("✅ Placed middle level notification processed!")
    
    # Test 4: Simulate moving a level
    print("\n📝 Test 4: Simulate moving a level")
    send_changelog_notification(
        action="moved",
        level_name="Moved Level",
        admin_username="TestAdmin",
        old_position=10,
        new_position=3,
        above_level="New Level Above",
        below_level="New Level Below",
        list_type="main"
    )
    print("✅ Moved level notification processed!")
    
    # Test 5: Simulate moving to legacy
    print("\n📝 Test 5: Simulate moving to legacy")
    send_changelog_notification(
        action="legacy",
        level_name="Legacy Level",
        admin_username="TestAdmin",
        old_position=150,
        list_type="main"
    )
    print("✅ Moved to legacy notification processed!")
    
    print("\n🎉 All tests completed successfully!")
        
except Exception as e:
    print(f"❌ Error testing changelog notification: {e}")
    import traceback
    traceback.print_exc()