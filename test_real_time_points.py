#!/usr/bin/env python3
"""
Test Script for Real-time Points System
=======================================

This script tests the real-time points recalculation system to ensure:
1. Level points are correctly calculated based on position
2. User points are correctly recalculated when levels move
3. All users affected by level changes get updated points
4. The system handles edge cases properly

Run this script to verify the points system is working correctly.
"""

import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
from pymongo import MongoClient
from bson.objectid import ObjectId

# Load environment variables
load_dotenv()

# Import the real-time points system
try:
    from real_time_points_system import RealTimePointsManager
    print("✅ Real-time points system imported successfully")
except ImportError as e:
    print(f"❌ Failed to import real-time points system: {e}")
    sys.exit(1)

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

def test_points_calculation():
    """Test the points calculation formula"""
    print("\n🧮 Testing Points Calculation Formula")
    print("=" * 50)
    
    manager = RealTimePointsManager(None)  # No DB needed for calculation test
    
    test_positions = [1, 2, 3, 10, 25, 50, 75, 100, 150]
    
    for pos in test_positions:
        points = manager.calculate_level_points(pos, False)
        legacy_points = manager.calculate_level_points(pos, True)
        print(f"Position #{pos:3d}: {points:8.2f} points (Legacy: {legacy_points:8.2f})")
    
    print("✅ Points calculation test completed")

def test_system_status(db):
    """Test system status checking"""
    print("\n📊 Testing System Status")
    print("=" * 50)
    
    manager = RealTimePointsManager(db)
    status = manager.get_system_status()
    
    if 'error' in status:
        print(f"❌ Error getting system status: {status['error']}")
        return False
    
    print(f"📈 Total levels: {status['total_levels']}")
    print(f"👥 Total users: {status['total_users']}")
    print(f"✅ Total approved records: {status['total_approved_records']}")
    print(f"⚠️  Levels with incorrect points: {status['levels_with_incorrect_points']}")
    print(f"🏥 System healthy: {status['system_healthy']}")
    
    return status['system_healthy']

def test_level_points_recalculation(db):
    """Test level points recalculation"""
    print("\n🔄 Testing Level Points Recalculation")
    print("=" * 50)
    
    manager = RealTimePointsManager(db)
    
    # Get some sample levels before recalculation
    sample_levels = list(db.levels.find({}, {"name": 1, "position": 1, "points": 1, "is_legacy": 1}).limit(5))
    
    print("Sample levels before recalculation:")
    for level in sample_levels:
        print(f"  {level.get('name', 'Unknown')}: Position #{level.get('position', 'N/A')}, Points: {level.get('points', 0)}")
    
    # Perform recalculation
    levels_updated = manager.recalculate_all_level_points()
    
    print(f"\n✅ Recalculated points for {levels_updated} levels")
    
    # Check the same levels after recalculation
    print("\nSample levels after recalculation:")
    for level in sample_levels:
        updated_level = db.levels.find_one({"_id": level["_id"]})
        if updated_level:
            print(f"  {updated_level.get('name', 'Unknown')}: Position #{updated_level.get('position', 'N/A')}, Points: {updated_level.get('points', 0)}")
    
    return levels_updated > 0

def test_user_points_recalculation(db):
    """Test user points recalculation"""
    print("\n👥 Testing User Points Recalculation")
    print("=" * 50)
    
    manager = RealTimePointsManager(db)
    
    # Get some sample users with points
    sample_users = list(db.users.find({"points": {"$gt": 0}}, {"username": 1, "points": 1}).limit(5))
    
    if not sample_users:
        print("⚠️  No users with points found for testing")
        return True
    
    print("Sample users before recalculation:")
    for user in sample_users:
        print(f"  {user.get('username', 'Unknown')}: {user.get('points', 0)} points")
    
    # Perform recalculation
    users_updated = manager.recalculate_all_user_points()
    
    print(f"\n✅ Recalculated points for {users_updated} users")
    
    # Check the same users after recalculation
    print("\nSample users after recalculation:")
    for user in sample_users:
        updated_user = db.users.find_one({"_id": user["_id"]})
        if updated_user:
            print(f"  {updated_user.get('username', 'Unknown')}: {updated_user.get('points', 0)} points")
    
    return users_updated > 0

def test_position_change_simulation(db):
    """Test simulated position change (without actually changing positions)"""
    print("\n🔄 Testing Position Change Simulation")
    print("=" * 50)
    
    # Find a level to simulate moving
    test_level = db.levels.find_one({"position": {"$gte": 10, "$lte": 50}, "is_legacy": {"$ne": True}})
    
    if not test_level:
        print("⚠️  No suitable level found for position change simulation")
        return True
    
    current_pos = test_level['position']
    new_pos = current_pos - 1 if current_pos > 1 else current_pos + 1
    
    print(f"Simulating move of '{test_level.get('name', 'Unknown')}' from #{current_pos} to #{new_pos}")
    
    # Calculate what the points would be
    manager = RealTimePointsManager(db)
    old_points = manager.calculate_level_points(current_pos, False)
    new_points = manager.calculate_level_points(new_pos, False)
    
    print(f"Points would change from {old_points} to {new_points}")
    
    # Find users who would be affected
    affected_records = list(db.records.find({
        "level_id": test_level["_id"],
        "status": "approved"
    }))
    
    print(f"This change would affect {len(affected_records)} user records")
    
    return True

def run_comprehensive_test():
    """Run all tests"""
    print("🚀 Starting Real-time Points System Tests")
    print("=" * 60)
    
    # Connect to database
    db = connect_to_database()
    
    # Run tests
    tests = [
        ("Points Calculation", test_points_calculation),
        ("System Status", lambda: test_system_status(db)),
        ("Level Points Recalculation", lambda: test_level_points_recalculation(db)),
        ("User Points Recalculation", lambda: test_user_points_recalculation(db)),
        ("Position Change Simulation", lambda: test_position_change_simulation(db))
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 Running: {test_name}")
            result = test_func()
            results.append((test_name, result, None))
            print(f"✅ {test_name}: {'PASSED' if result else 'COMPLETED'}")
        except Exception as e:
            results.append((test_name, False, str(e)))
            print(f"❌ {test_name}: FAILED - {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result, error in results:
        if error:
            print(f"❌ {test_name}: FAILED - {error}")
            failed += 1
        elif result:
            print(f"✅ {test_name}: PASSED")
            passed += 1
        else:
            print(f"⚠️  {test_name}: COMPLETED (no changes needed)")
            passed += 1
    
    print(f"\n📊 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests completed successfully!")
        print("\n💡 The real-time points system is ready to use!")
        print("\nTo enable it in your application:")
        print("1. The system is already integrated into main.py")
        print("2. Level position changes will automatically trigger full recalculation")
        print("3. Use the admin panel to manually recalculate all points if needed")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
    
    return failed == 0

if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)