#!/usr/bin/env python3
"""
Test Enhanced Changelog Messaging
=================================

This script tests the enhanced changelog messaging for:
1. New #1 placements with dethroning
2. Level moves to #1 with dethroning  
3. Any placement that pushes levels to legacy
4. Moves that push levels out of top 10
"""

import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables
load_dotenv()

def connect_to_database():
    """Connect to MongoDB database"""
    try:
        mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
        mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')
        
        client = MongoClient(mongodb_uri)
        db = client[mongodb_db]
        
        # Test connection
        client.admin.command('ping')
        print(f"✅ Connected to database: {mongodb_db}")
        
        return db
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)

def test_changelog_messages():
    """Test the enhanced changelog messaging system"""
    print("🧪 Testing Enhanced Changelog Messages")
    print("=" * 60)
    
    # Import the changelog function
    try:
        # Add the current directory to Python path so we can import from main.py
        sys.path.insert(0, '.')
        from main import send_enhanced_changelog_notification
        print("✅ Imported changelog function successfully")
    except ImportError as e:
        print(f"❌ Failed to import changelog function: {e}")
        return False
    
    # Test scenarios
    test_scenarios = [
        {
            "name": "New Level Placed at #1 (Dethroning)",
            "action": "placed",
            "level_name": "Bloodlust",
            "admin_username": "TestAdmin",
            "kwargs": {
                "position": 1,
                "dethroned_level": "Tartarus",
                "pushed_to_legacy": "Cataclysm",
                "list_type": "main"
            },
            "expected_contains": ["placed at #1", "dethroning Tartarus", "pushes Cataclysm to the legacy list"]
        },
        {
            "name": "Level Moved to #1 (Dethroning)",
            "action": "moved", 
            "level_name": "Zodiac",
            "admin_username": "TestAdmin",
            "kwargs": {
                "old_position": 5,
                "new_position": 1,
                "dethroned_level": "Bloodlust",
                "list_type": "main"
            },
            "expected_contains": ["moved from #5 to #1", "dethroning Bloodlust"]
        },
        {
            "name": "Regular Placement with Legacy Push",
            "action": "placed",
            "level_name": "Sonic Wave",
            "admin_username": "TestAdmin", 
            "kwargs": {
                "position": 50,
                "above_level": "Yatagarasu",
                "below_level": "Plasma Pulse Finale",
                "pushed_to_legacy": "Old Level",
                "list_type": "main"
            },
            "expected_contains": ["placed at #50", "below Yatagarasu", "above Plasma Pulse Finale", "pushes Old Level to the legacy list"]
        },
        {
            "name": "Move with Top 10 Push",
            "action": "moved",
            "level_name": "Firework",
            "admin_username": "TestAdmin",
            "kwargs": {
                "old_position": 15,
                "new_position": 8,
                "pushed_out_of_top10": "Conical Depression",
                "list_type": "main"
            },
            "expected_contains": ["moved from #15 to #8", "pushes Conical Depression out of the top 10"]
        },
        {
            "name": "Legacy List Placement",
            "action": "placed",
            "level_name": "The Hell Field",
            "admin_username": "TestAdmin",
            "kwargs": {
                "position": 25,
                "list_type": "legacy"
            },
            "expected_contains": ["placed at #25", "from the legacy list"]
        }
    ]
    
    # Run tests
    passed = 0
    failed = 0
    
    for scenario in test_scenarios:
        print(f"\n🧪 Testing: {scenario['name']}")
        print("-" * 40)
        
        try:
            # Capture the message by temporarily redirecting the notification
            captured_message = None
            
            # Mock the notify_changelog function to capture the message
            original_notify = None
            try:
                import main
                original_notify = main.notify_changelog
                
                def capture_message(message, admin_username=None):
                    nonlocal captured_message
                    captured_message = message
                    print(f"📝 Generated message: {message}")
                    return True
                
                main.notify_changelog = capture_message
                main.CHANGELOG_DISCORD_AVAILABLE = True
                
                # Call the function
                send_enhanced_changelog_notification(
                    scenario["action"],
                    scenario["level_name"], 
                    scenario["admin_username"],
                    **scenario["kwargs"]
                )
                
                # Check if message contains expected elements
                if captured_message:
                    all_found = True
                    for expected in scenario["expected_contains"]:
                        if expected.lower() not in captured_message.lower():
                            print(f"❌ Missing expected text: '{expected}'")
                            all_found = False
                        else:
                            print(f"✅ Found: '{expected}'")
                    
                    if all_found:
                        print(f"✅ Test PASSED")
                        passed += 1
                    else:
                        print(f"❌ Test FAILED")
                        failed += 1
                else:
                    print(f"❌ No message generated")
                    failed += 1
                    
            finally:
                # Restore original function
                if original_notify:
                    main.notify_changelog = original_notify
                    
        except Exception as e:
            print(f"❌ Test error: {e}")
            failed += 1
    
    # Summary
    print(f"\n" + "=" * 60)
    print(f"📊 TEST RESULTS")
    print(f"=" * 60)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success Rate: {(passed/(passed+failed)*100):.1f}%" if (passed+failed) > 0 else "N/A")
    
    if failed == 0:
        print(f"\n🎉 All tests passed! The enhanced changelog messaging is working correctly.")
        print(f"\n💡 Your changelog bot will now:")
        print(f"   • Say 'X has been placed at #1, dethroning Y' for new #1 levels")
        print(f"   • Say 'This pushes Z to the legacy list' when levels get pushed to legacy")
        print(f"   • Include dethroning info for any move to #1")
        print(f"   • Show what gets pushed out of top 10")
    else:
        print(f"\n⚠️  Some tests failed. Check the output above for details.")
    
    return failed == 0

if __name__ == "__main__":
    try:
        success = test_changelog_messages()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)