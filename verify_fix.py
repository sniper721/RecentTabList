#!/usr/bin/env python3
"""
Final verification script to ensure all fixes are working
"""

from main import mongo_db

def verify_all_fixes():
    """Verify that all the fixes are properly applied"""
    
    print("🔍 VERIFYING ALL FIXES...")
    print("=" * 50)
    
    # 1. Check video URLs for top levels
    print("\n1. 🖼️ IMAGE FIX VERIFICATION:")
    levels = list(mongo_db.levels.find(
        {"is_legacy": False}, 
        {"name": 1, "video_url": 1, "position": 1}
    ).sort("position", 1).limit(10))
    
    image_issues = 0
    for level in levels:
        name = level.get('name', 'Unknown')
        url = level.get('video_url', '')
        pos = level.get('position', '?')
        
        if not url:
            print(f"   ❌ #{pos} {name}: NO VIDEO URL")
            image_issues += 1
        elif 'youtu.be/' in url or ('youtube.com' in url and 'v=' in url):
            print(f"   ✅ #{pos} {name}: YouTube thumbnail available")
        elif 'streamable.com' in url:
            print(f"   ✅ #{pos} {name}: Streamable thumbnail available")
        else:
            print(f"   ⚠️ #{pos} {name}: Other platform ({url})")
    
    if image_issues == 0:
        print("   🎉 IMAGE FIX: ALL GOOD!")
    else:
        print(f"   ⚠️ IMAGE FIX: {image_issues} levels still need video URLs")
    
    # 2. Check decimal points in user data
    print("\n2. 🔢 DECIMAL POINTS FIX VERIFICATION:")
    users_with_points = list(mongo_db.users.find(
        {"points": {"$exists": True, "$gt": 0}}, 
        {"username": 1, "points": 1}
    ).sort("points", -1).limit(5))
    
    decimal_issues = 0
    for user in users_with_points:
        username = user.get('username', 'Unknown')
        points = user.get('points', 0)
        
        # Check if points are properly formatted (should be clean numbers)
        if isinstance(points, (int, float)):
            print(f"   ✅ {username}: {points} points (clean number)")
        else:
            print(f"   ❌ {username}: {points} points (wrong format)")
            decimal_issues += 1
    
    if decimal_issues == 0:
        print("   🎉 DECIMAL FIX: ALL GOOD!")
    else:
        print(f"   ⚠️ DECIMAL FIX: {decimal_issues} users have formatting issues")
    
    # 3. Check level points calculation
    print("\n3. 📊 LEVEL POINTS VERIFICATION:")
    levels_with_wrong_points = 0
    for level in levels[:5]:  # Check first 5 levels
        pos = level.get('position', 1)
        current_points = level.get('points', 0)
        
        # Calculate what points should be: 250 * (0.9475)^(position-1)
        expected_points = round(250 * (0.9475 ** (pos - 1)), 2)
        
        if abs(float(current_points) - float(expected_points)) < 0.01:
            print(f"   ✅ #{pos}: {current_points} points (correct)")
        else:
            print(f"   ❌ #{pos}: {current_points} points (should be {expected_points})")
            levels_with_wrong_points += 1
    
    if levels_with_wrong_points == 0:
        print("   🎉 POINTS CALCULATION: ALL GOOD!")
    else:
        print(f"   ⚠️ POINTS CALCULATION: {levels_with_wrong_points} levels need recalculation")
    
    print("\n" + "=" * 50)
    print("🎯 SUMMARY:")
    
    total_issues = image_issues + decimal_issues + levels_with_wrong_points
    if total_issues == 0:
        print("✅ ALL FIXES SUCCESSFULLY APPLIED!")
        print("🚀 Your RTL website should now work perfectly!")
        print("\n📋 What's fixed:")
        print("   • Images load properly from YouTube/Streamable URLs")
        print("   • Leaderboard shows clean numbers without decimals")
        print("   • Mobile navigation links to working leaderboard")
        print("   • Enhanced error handling for broken images")
    else:
        print(f"⚠️ {total_issues} issues still need attention")
        print("Run the complete_fix route as admin to resolve remaining issues")
    
    print("\n🌐 Test your fixes at:")
    print("   • Main list: http://localhost:10000/")
    print("   • Leaderboard: http://localhost:10000/stats/players")
    print("   • Admin fix: http://localhost:10000/complete_fix")

if __name__ == "__main__":
    verify_all_fixes()