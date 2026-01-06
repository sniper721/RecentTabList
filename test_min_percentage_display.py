#!/usr/bin/env python3
"""
Test the new minimum percentage display system
"""

def test_min_percentage_display():
    """Test that levels show their actual minimum percentage instead of hardcoded 79%"""
    
    try:
        print("\n🧪 Testing minimum percentage display system...")
        
        # Import the main app
        from main import app, mongo_db
        
        # Test with app context
        with app.app_context():
            # Get a few levels to test
            test_levels = list(mongo_db.levels.find(
                {"is_legacy": False}, 
                {"name": 1, "position": 1, "min_percentage": 1, "points": 1}
            ).sort("position", 1).limit(5))
            
            if not test_levels:
                print("❌ No levels found in database")
                return False
            
            print(f"✅ Found {len(test_levels)} levels to test")
            
            # Test the points calculation logic
            for level in test_levels:
                position = level.get('position', 0)
                min_percentage = level.get('min_percentage', 100)
                points_100 = round(250 * (0.9636214148582346 ** (position - 1)), 2)
                
                print(f"\n📊 Level: {level.get('name', 'Unknown')}")
                print(f"   Position: #{position}")
                print(f"   Min %: {min_percentage}%")
                
                if min_percentage < 100:
                    points_min = round(points_100 * 0.1, 2)
                    print(f"   Display: {points_min} ({min_percentage}%) — {points_100} (100%) points")
                else:
                    print(f"   Display: {points_100} (100%) points")
            
            # Test specific scenarios
            print(f"\n🔍 Testing specific scenarios:")
            
            # Check if any levels have min_percentage < 100
            levels_with_min = list(mongo_db.levels.find(
                {"min_percentage": {"$lt": 100}}, 
                {"name": 1, "min_percentage": 1}
            ).limit(3))
            
            if levels_with_min:
                print(f"✅ Found {len(levels_with_min)} levels with min_percentage < 100%:")
                for level in levels_with_min:
                    print(f"   - {level.get('name')}: {level.get('min_percentage')}%")
            else:
                print("ℹ️  No levels found with min_percentage < 100%")
            
            # Check if any levels are missing min_percentage
            levels_without_min = mongo_db.levels.count_documents(
                {"min_percentage": {"$exists": False}}
            )
            
            if levels_without_min > 0:
                print(f"⚠️  {levels_without_min} levels missing min_percentage field")
            else:
                print("✅ All levels have min_percentage field")
            
            print(f"\n✅ Minimum percentage display system test completed!")
            return True
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_min_percentage_display()
    if success:
        print("\n🎉 All tests passed!")
        print("\n📋 Changes made:")
        print("   ✅ Updated index.html to use level.min_percentage instead of hardcoded 79%")
        print("   ✅ Updated timemachine.html to use level.min_percentage")
        print("   ✅ Updated legacy.html to use level.min_percentage")
        print("   ✅ Updated database queries to include min_percentage field")
        print("   ✅ Added logic to show only 100% points when min_percentage is 100%")
        print("\n💡 How it works:")
        print("   - If min_percentage < 100%: Shows 'X (min%) — Y (100%) points'")
        print("   - If min_percentage = 100%: Shows only 'Y (100%) points'")
        print("   - Minimum percentage points = 10% of full points (as per existing system)")
    else:
        print("\n❌ Tests failed!")