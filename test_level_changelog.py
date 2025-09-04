#!/usr/bin/env python3
"""
Test script for level changelog Discord notifications
"""

import os
import sys
from datetime import datetime, timezone

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the Discord integration
try:
    from discord_integration import notify_level_changelog
    print("✅ Discord integration imported successfully")
except Exception as e:
    print(f"❌ Failed to import Discord integration: {e}")
    sys.exit(1)

def test_level_changelog():
    """Test the level changelog notification system"""
    print("🧪 Testing level changelog notifications...")
    
    # Test data for different scenarios
    test_cases = [
        {
            "action": "placed",
            "level_name": "Test Level",
            "position": 1,
            "below_level": "Previous #1",
            "admin": "TestAdmin",
            "list_type": "main"
        },
        {
            "action": "placed",
            "level_name": "Another Level",
            "position": 5,
            "above_level": "Level Above",
            "below_level": "Level Below",
            "admin": "TestAdmin",
            "list_type": "main"
        },
        {
            "action": "moved",
            "level_name": "Moving Level",
            "old_position": 10,
            "new_position": 3,
            "admin": "TestAdmin",
            "list_type": "main"
        },
        {
            "action": "legacy",
            "level_name": "Old Level",
            "old_position": 75,
            "admin": "TestAdmin",
            "list_type": "legacy"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test case {i}: {test_case['action']} - {test_case['level_name']}")
        try:
            # Add timestamp to the test case
            test_case_with_timestamp = {
                "timestamp": datetime.now(timezone.utc),
                **test_case
            }
            
            # Send notification
            notify_level_changelog(test_case_with_timestamp)
            print("✅ Notification sent successfully")
        except Exception as e:
            print(f"❌ Failed to send notification: {e}")
    
    print("\n🏁 Test completed!")

if __name__ == "__main__":
    test_level_changelog()