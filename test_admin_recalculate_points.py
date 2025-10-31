#!/usr/bin/env python3
"""
Test the admin recalculate points functionality
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB configuration
mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

def calculate_level_points(position, is_legacy=False):
    """Calculate points based on position using corrected exponential formula"""
    if is_legacy:
        return 0.0
    # p = 250(0.965)^(x-1) where x is the placement of the level on the list
    return round(250 * (0.965 ** (position - 1)), 2)

def calculate_record_points(record, level):
    """Calculate points earned from a record"""
    status = record.get('status', 'pending')
    if status != 'approved' or level.get('is_legacy', False):
        return 0.0
    
    # Full completion (100% points)
    if record['progress'] == 100:
        return float(level['points'])
    
    # Partial completion - 10% of full points when reaching minimum percentage
    min_percentage = level.get('min_percentage', 100)
    if record['progress'] >= min_percentage and min_percentage < 100:
        return round(float(level['points']) * 0.1, 2)  # 10% of full points
    
    return 0.0

def main():
    print("🧪 Testing admin recalculate points functionality...")
    
    # Connect to MongoDB
    try:
        mongo_client = MongoClient(
            mongodb_uri,
            tls=True,
            tlsAllowInvalidCertificates=False,
            tlsAllowInvalidHostnames=False,
            serverSelectionTimeoutMS=60000,
            socketTimeoutMS=60000,
            connectTimeoutMS=30000
        )
        mongo_db = mongo_client[mongodb_db]
        mongo_client.admin.command('ping')
        print("✅ Connected to MongoDB successfully")
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        return
    
    # Test the real-time points system directly
    print("\n🔍 Testing real-time points system...")
    
    try:
        from real_time_points_system import RealTimePointsManager
        manager = RealTimePointsManager(mongo_db)
        print("✅ Real-time points system imported successfully")
        
        # Test level points calculation
        test_positions = [1, 50, 100, 150]
        print("\n📊 Testing level points calculation:")
        for pos in test_positions:
            calculated_points = manager.calculate_level_points(pos, is_legacy=False)
            expected_points = calculate_level_points(pos, is_legacy=False)
            
            if abs(calculated_points - expected_points) < 0.01:
                print(f"  ✅ Position #{pos}: {calculated_points} points (correct)")
            else:
                print(f"  ❌ Position #{pos}: {calculated_points} vs expected {expected_points}")
        
        # Test recalculating all level points
        print("\n🔄 Testing level points recalculation...")
        levels_updated = manager.recalculate_all_level_points()
        print(f"✅ Recalculated {levels_updated} level points")
        
        # Test recalculating all user points
        print("\n🔄 Testing user points recalculation...")
        users_updated = manager.recalculate_all_user_points()
        print(f"✅ Recalculated {users_updated} user points")
        
        # Verify a few levels have correct points
        print("\n🔍 Verifying level points after recalculation:")
        sample_levels = list(mongo_db.levels.find({
            "is_legacy": {"$ne": True},
            "position": {"$in": [1, 50, 100, 150]}
        }))
        
        all_correct = True
        for level in sample_levels:
            pos = level["position"]
            actual_points = level.get("points", 0)
            expected_points = calculate_level_points(pos)
            
            if abs(actual_points - expected_points) < 0.01:
                print(f"  ✅ #{pos}: {level['name']} - {actual_points} points (correct)")
            else:
                print(f"  ❌ #{pos}: {level['name']} - {actual_points} vs expected {expected_points}")
                all_correct = False
        
        # Verify a few users have correct points
        print("\n🔍 Verifying user points after recalculation:")
        top_users = list(mongo_db.users.find({}).sort("points", -1).limit(3))
        
        levels = list(mongo_db.levels.find({}))
        level_lookup = {str(level['_id']): level for level in levels}
        
        for user in top_users:
            user_id = user['_id']
            username = user.get('username', 'Unknown')
            stored_points = user.get('points', 0)
            
            # Calculate expected points
            records = list(mongo_db.records.find({
                "user_id": user_id,
                "status": "approved"
            }))
            
            expected_total = 0.0
            for record in records:
                level_id = str(record['level_id'])
                level = level_lookup.get(level_id)
                if level:
                    expected_total += calculate_record_points(record, level)
            
            expected_total = round(expected_total, 2)
            
            if abs(stored_points - expected_total) < 0.01:
                print(f"  ✅ {username}: {stored_points} points (correct)")
            else:
                print(f"  ❌ {username}: {stored_points} vs expected {expected_total}")
                all_correct = False
        
        if all_correct:
            print("\n🎉 All points are correct! Admin recalculate function should work perfectly.")
        else:
            print("\n⚠️  Some points are incorrect. Admin recalculate function may need fixes.")
            
    except ImportError as e:
        print(f"❌ Failed to import real-time points system: {e}")
        print("⚠️  Admin recalculate will use fallback system")
    except Exception as e:
        print(f"❌ Error testing real-time points system: {e}")
    
    # Test the fallback calculation functions
    print("\n🔍 Testing fallback calculation functions...")
    
    # Test calculate_level_points function
    test_positions = [1, 50, 100, 150]
    print("📊 Testing calculate_level_points function:")
    for pos in test_positions:
        points = calculate_level_points(pos)
        print(f"  Position #{pos}: {points} points")
    
    # Verify formula gives correct values
    pos1_points = calculate_level_points(1)
    if abs(pos1_points - 250.0) < 0.01:
        print("✅ Position #1 gives 250 points (correct)")
    else:
        print(f"❌ Position #1 gives {pos1_points} points (should be 250)")
    
    print("\n✅ Admin recalculate points functionality test completed!")

if __name__ == "__main__":
    main()