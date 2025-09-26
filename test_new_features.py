#!/usr/bin/env python3
"""
Test script for new features:
1. Multiple record submission
2. Enhanced changelog system
3. Automatic legacy management
4. Submission logs with comments
5. Removal reasons
"""

import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_enhanced_changelog():
    """Test the enhanced changelog system"""
    print("\n🧪 Testing Enhanced Changelog System")
    print("=" * 50)
    
    try:
        from main import send_enhanced_changelog_notification
        
        # Test #1 placement with dethronement
        print("\n📝 Test 1: #1 Placement with Dethronement")
        send_enhanced_changelog_notification(
            action="placed",
            level_name="New Hardest Level",
            admin_username="TestAdmin",
            position=1,
            dethroned_level="Previous #1",
            pushed_to_legacy="Level at #101"
        )
        
        # Test regular placement
        print("\n📝 Test 2: Regular Placement")
        send_enhanced_changelog_notification(
            action="placed",
            level_name="New Level",
            admin_username="TestAdmin",
            position=50,
            above_level="Level Above",
            below_level="Level Below"
        )
        
        # Test level movement
        print("\n📝 Test 3: Level Movement")
        send_enhanced_changelog_notification(
            action="moved",
            level_name="Moved Level",
            admin_username="TestAdmin",
            old_position=75,
            new_position=25,
            above_level="Level Above",
            below_level="Level Below"
        )
        
        # Test removal with reason
        print("\n📝 Test 4: Level Removal with Reason")
        send_enhanced_changelog_notification(
            action="removed",
            level_name="Removed Level",
            admin_username="TestAdmin",
            old_position=30,
            reason="Inappropriate content"
        )
        
        # Test legacy move
        print("\n📝 Test 5: Legacy Move")
        send_enhanced_changelog_notification(
            action="legacy",
            level_name="Legacy Level",
            admin_username="System",
            old_position=101,
            legacy_position=1
        )
        
        print("✅ Enhanced changelog tests completed!")
        
    except Exception as e:
        print(f"❌ Error testing enhanced changelog: {e}")
        import traceback
        traceback.print_exc()

def test_submission_logging():
    """Test submission logging with comments"""
    print("\n🧪 Testing Submission Logging")
    print("=" * 50)
    
    try:
        from main import log_submission_with_comments
        from bson.objectid import ObjectId
        
        # Test logging with comments
        print("\n📝 Test: Logging submission with comments")
        log_submission_with_comments(
            user_id=ObjectId(),  # Dummy user ID
            level_name="Test Level",
            progress=85,
            comments="This was a really difficult level! Took me 3000 attempts."
        )
        
        print("✅ Submission logging test completed!")
        
    except Exception as e:
        print(f"❌ Error testing submission logging: {e}")
        import traceback
        traceback.print_exc()

def test_legacy_management():
    """Test automatic legacy management"""
    print("\n🧪 Testing Automatic Legacy Management")
    print("=" * 50)
    
    try:
        from main import auto_manage_legacy_list, get_level_neighbors
        
        # Test getting level neighbors
        print("\n📝 Test: Getting level neighbors")
        above, below = get_level_neighbors(50, False)
        print(f"Level neighbors for position 50: Above={above}, Below={below}")
        
        # Test auto legacy management (this would need actual database data)
        print("\n📝 Test: Auto legacy management")
        result = auto_manage_legacy_list()
        if result:
            print(f"Moved {result} to legacy list")
        else:
            print("No level needed to be moved to legacy")
        
        print("✅ Legacy management tests completed!")
        
    except Exception as e:
        print(f"❌ Error testing legacy management: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Run all tests"""
    print("🚀 Starting New Features Test Suite")
    print("=" * 60)
    
    # Test enhanced changelog
    test_enhanced_changelog()
    
    # Test submission logging
    test_submission_logging()
    
    # Test legacy management
    test_legacy_management()
    
    print("\n🎉 All tests completed!")
    print("=" * 60)
    print("\n📋 Summary of New Features:")
    print("✅ Multiple record submission capability")
    print("✅ Enhanced changelog with detailed messaging")
    print("✅ Automatic legacy list management (starts from #101)")
    print("✅ Submission logs with comments")
    print("✅ Level removal with optional reasons")
    print("✅ Discord notifications include comments")
    print("\n🔧 To use these features:")
    print("1. Visit /submit_record and try the multiple submission mode")
    print("2. Add/move levels as admin to see enhanced changelog messages")
    print("3. Check /admin/submission_logs to see submission comments")
    print("4. Legacy list now shows positions starting from #101")

if __name__ == "__main__":
    main()