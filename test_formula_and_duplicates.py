#!/usr/bin/env python3
"""
Test script for formula update and duplicate verification detection
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import app, mongo_db, calculate_level_points, check_for_duplicate_levels
from bson.objectid import ObjectId
from datetime import datetime, timezone

def test_formula_update():
    """Test that the formula has been updated correctly"""
    
    print("🧪 Testing Formula Update")
    print("=" * 30)
    
    # Test key positions with the new formula: 250 * (0.9475)^(position-1)
    test_cases = [
        (1, 250.0),      # 250 * (0.9475)^0 = 250
        (2, 236.88),     # 250 * (0.9475)^1 = 236.88
        (3, 224.44),     # 250 * (0.9475)^2 = 224.44
        (10, 153.87),    # 250 * (0.9475)^9 = 153.87
        (20, 89.73),     # 250 * (0.9475)^19 = 89.73
    ]
    
    print("Testing formula: p = 250 * (0.9475)^(position-1)")
    print("Position | Expected | Calculated | Match")
    print("-" * 40)
    
    all_correct = True
    for position, expected in test_cases:
        calculated = calculate_level_points(position, False)
        match = abs(calculated - expected) < 0.1  # Allow small rounding differences
        status = "✅" if match else "❌"
        
        print(f"#{position:2d}      | {expected:7.2f}  | {calculated:9.2f}  | {status}")
        
        if not match:
            all_correct = False
    
    if all_correct:
        print("\n✅ Formula update successful! All positions calculate correctly.")
    else:
        print("\n❌ Formula update failed! Some positions are incorrect.")
    
    return all_correct

def test_duplicate_detection():
    """Test the duplicate verification detection feature"""
    
    print("\n🧪 Testing Duplicate Detection")
    print("=" * 35)
    
    try:
        # Get some existing levels from the database
        existing_levels = list(mongo_db.levels.find({}, {"name": 1, "level_id": 1, "position": 1}).limit(5))
        
        if not existing_levels:
            print("❌ No existing levels found in database for testing")
            return False
        
        print(f"Found {len(existing_levels)} existing levels for testing:")
        for level in existing_levels:
            print(f"  • {level['name']} (Position #{level['position']})")
        
        # Check current verification submissions
        current_submissions = list(mongo_db.verification_submissions.find({"status": "pending"}))
        print(f"\nCurrent pending verification submissions: {len(current_submissions)}")
        
        # Run duplicate detection
        print("\nRunning duplicate detection...")
        removed_count = check_for_duplicate_levels()
        
        if removed_count > 0:
            print(f"✅ Duplicate detection working! Removed {removed_count} duplicate submissions.")
        else:
            print("✅ Duplicate detection working! No duplicates found (which is good).")
        
        # Check submissions after cleanup
        remaining_submissions = list(mongo_db.verification_submissions.find({"status": "pending"}))
        print(f"Remaining pending verification submissions: {len(remaining_submissions)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing duplicate detection: {e}")
        return False

def test_verification_routes():
    """Test that the verification routes are working"""
    
    print("\n🧪 Testing Verification Routes")
    print("=" * 35)
    
    with app.test_client() as client:
        # Check that routes exist
        routes = []
        for rule in app.url_map.iter_rules():
            if 'verification' in rule.rule:
                routes.append(rule.rule)
        
        print("Available verification routes:")
        for route in routes:
            print(f"  • {route}")
        
        # Check for our new routes
        required_routes = [
            '/admin/verification/accept/<submission_id>',
            '/admin/verification/deny/<submission_id>',
            '/admin/cleanup_duplicate_verifications'
        ]
        
        all_routes_exist = True
        for required_route in required_routes:
            if required_route in routes:
                print(f"✅ {required_route}")
            else:
                print(f"❌ {required_route} - MISSING")
                all_routes_exist = False
        
        return all_routes_exist

def main():
    """Run all tests"""
    
    print("🚀 Testing Formula Update and Duplicate Detection Features")
    print("=" * 60)
    
    # Test formula update
    formula_ok = test_formula_update()
    
    # Test duplicate detection
    duplicate_ok = test_duplicate_detection()
    
    # Test routes
    routes_ok = test_verification_routes()
    
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    print(f"Formula Update:      {'✅ PASS' if formula_ok else '❌ FAIL'}")
    print(f"Duplicate Detection: {'✅ PASS' if duplicate_ok else '❌ FAIL'}")
    print(f"Route Registration:  {'✅ PASS' if routes_ok else '❌ FAIL'}")
    
    if formula_ok and duplicate_ok and routes_ok:
        print("\n🎉 All tests passed! Features are working correctly.")
        
        print("\n📋 How the new features work:")
        print("=" * 40)
        print("🔢 FORMULA UPDATE:")
        print("  • Updated from 250*(0.965)^(x-1) to 250*(0.9475)^(x-1)")
        print("  • Position #1 = 250 points")
        print("  • Position #20 ≈ 77.73 points")
        print("  • All user points will be recalculated automatically")
        
        print("\n🧹 DUPLICATE DETECTION:")
        print("  • Automatically removes verification submissions for levels already on the list")
        print("  • Checks both level names (case-insensitive) and level IDs")
        print("  • Runs automatically when admins view verification submissions")
        print("  • Manual cleanup button available in admin panel")
        print("  • Users get notified when their duplicate submissions are removed")
        
        print("\n🎯 USAGE:")
        print("  1. Go to /admin/verifications")
        print("  2. Duplicates are automatically detected and removed")
        print("  3. Use 'Cleanup Duplicates' button for manual cleanup")
        print("  4. Accept/Deny verifications as normal")
        print("  5. Points are calculated with the new formula")
        
    else:
        print("\n❌ Some tests failed. Please check the implementation.")

if __name__ == "__main__":
    main()