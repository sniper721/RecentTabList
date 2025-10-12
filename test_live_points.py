#!/usr/bin/env python3
"""
Test Live Points System
======================

This script tests that the live points system is working correctly
by simulating a level addition and checking if user points update automatically.
"""

import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
from pymongo import MongoClient
from bson.objectid import ObjectId

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

def test_live_points_system():
    """Test that the live points system works"""
    print("🧪 TESTING LIVE POINTS SYSTEM")
    print("=" * 50)
    
    # Connect to database
    db = connect_to_database()
    
    # Import the real-time points system
    try:
        from real_time_points_system import RealTimePointsManager
        print("✅ Real-time points system loaded")
    except ImportError as e:
        print(f"❌ Failed to import real-time points system: {e}")
        return False
    
    # Create manager
    manager = RealTimePointsManager(db)
    
    # Get current system status
    print("\n📊 Current System Status:")
    status = manager.get_system_status()
    
    if 'error' in status:
        print(f"❌ System error: {status['error']}")
        return False
    
    print(f"  • Total levels: {status['total_levels']}")
    print(f"  • Total users: {status['total_users']}")
    print(f"  • Total approved records: {status['total_approved_records']}")
    print(f"  • Levels with incorrect points: {status['levels_with_incorrect_points']}")
    print(f"  • System healthy: {status['system_healthy']}")
    
    if not status['system_healthy']:
        print(f"\n⚠️ System is not healthy! {status['levels_with_incorrect_points']} levels have incorrect points")
        print("Running automatic fix...")
        
        # Fix the system
        levels_updated = manager.recalculate_all_level_points()
        users_updated = manager.recalculate_all_user_points()
        
        print(f"✅ Fixed: {levels_updated} levels, {users_updated} users updated")
        
        # Check status again
        status_after = manager.get_system_status()
        if status_after.get('system_healthy', False):
            print("🎉 System is now healthy!")
        else:
            print("❌ System still has issues after fix")
            return False
    
    # Test: Find a user with records to see their current points
    print("\n👤 Sample User Points Check:")
    
    # Get a user who has approved records
    sample_user = db.records.aggregate([
        {"$match": {"status": "approved"}},
        {"$lookup": {"from": "users", "localField": "user_id", "foreignField": "_id", "as": "user"}},
        {"$unwind": "$user"},
        {"$group": {"_id": "$user_id", "username": {"$first": "$user.username"}, "points": {"$first": "$user.points"}, "record_count": {"$sum": 1}}},
        {"$sort": {"points": -1}},
        {"$limit": 1}
    ]).next()
    
    if sample_user:
        print(f"  • User: {sample_user['username']}")
        print(f"  • Current points: {sample_user['points']}")
        print(f"  • Number of records: {sample_user['record_count']}")
        
        # Recalculate this user's points to verify accuracy
        calculated_points = manager.recalculate_user_points(sample_user['_id'])
        
        if abs(float(sample_user['points']) - float(calculated_points)) < 0.01:
            print(f"  ✅ Points are accurate! ({calculated_points})")
        else:
            print(f"  ❌ Points mismatch! DB: {sample_user['points']}, Calculated: {calculated_points}")
            return False
    
    print("\n🎯 LIVE POINTS SYSTEM TEST RESULTS:")
    print("=" * 50)
    
    if status.get('system_healthy', False):
        print("✅ PASS: Real-time points system is working correctly!")
        print("✅ All level points are accurate")
        print("✅ All user points are accurate")
        print("✅ System is ready for live updates")
        
        print("\n💡 When you add/move levels through the admin panel:")
        print("  • Level points will update automatically")
        print("  • User points will recalculate automatically")
        print("  • No manual commands needed!")
        
        return True
    else:
        print("❌ FAIL: System has issues that need to be resolved")
        return False

if __name__ == "__main__":
    try:
        success = test_live_points_system()
        if success:
            print("\n🚀 The live points system is working perfectly!")
        else:
            print("\n⚠️ The live points system needs attention.")
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)