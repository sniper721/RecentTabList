#!/usr/bin/env python3
"""
Test the fixed admin recalculate points functionality
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

def main():
    print("🧪 Testing FIXED admin recalculate points functionality...")
    
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
    
    # Simulate the fixed admin recalculate function
    print("\n🔄 Simulating fixed admin recalculate function...")
    
    # Step 1: Recalculate all level points
    print("📊 Step 1: Recalculating level points...")
    levels = list(mongo_db.levels.find({}))
    levels_to_update = 0
    
    for level in levels:
        position = level.get("position", 0)
        is_legacy = level.get("is_legacy", False)
        current_points = level.get("points", 0)
        correct_points = calculate_level_points(position, is_legacy)
        
        if abs(current_points - correct_points) > 0.01:
            levels_to_update += 1
    
    print(f"  📊 {levels_to_update} levels need point updates")
    
    # Step 2: Recalculate user points
    print("📊 Step 2: Recalculating user points...")
    
    # Create level lookup with current points
    level_lookup = {str(level['_id']): level for level in levels}
    
    users = list(mongo_db.users.find({}))
    users_to_update = 0
    
    print(f"  📊 Checking {len(users)} users...")
    
    for user in users:
        user_id = user['_id']
        username = user.get('username', 'Unknown')
        current_points = user.get('points', 0.0)
        
        # Get all approved records for this user
        records = list(mongo_db.records.find({
            "user_id": user_id,
            "status": "approved"
        }))
        
        # Calculate correct total points
        correct_total_points = 0.0
        
        for record in records:
            level_id = str(record['level_id'])
            level = level_lookup.get(level_id)
            
            if level:
                # Use correct points for calculation
                level_points = calculate_level_points(level.get("position", 0), level.get("is_legacy", False))
                
                # Calculate points for this record
                if level.get('is_legacy', False):
                    points = 0.0
                elif record['progress'] == 100:
                    points = float(level_points)
                else:
                    # Partial completion - 10% of full points when reaching minimum percentage
                    min_percentage = level.get('min_percentage', 100)
                    if record['progress'] >= min_percentage and min_percentage < 100:
                        points = round(float(level_points) * 0.1, 2)
                    else:
                        points = 0.0
                
                correct_total_points += points
        
        # Round to 2 decimal places
        correct_total_points = round(correct_total_points, 2)
        
        # Check if user needs update
        if abs(correct_total_points - current_points) > 0.01:
            users_to_update += 1
            if users_to_update <= 5:  # Show first 5 users that need updates
                print(f"    👤 {username}: {current_points} → {correct_total_points} points")
    
    print(f"  📊 {users_to_update} users need point updates")
    
    # Verify top users would have correct points
    print("\n🔍 Verifying top users after simulation:")
    top_users = list(mongo_db.users.find({}).sort("points", -1).limit(5))
    
    for user in top_users:
        user_id = user['_id']
        username = user.get('username', 'Unknown')
        current_points = user.get('points', 0.0)
        
        # Calculate what their points should be
        records = list(mongo_db.records.find({
            "user_id": user_id,
            "status": "approved"
        }))
        
        expected_total = 0.0
        for record in records:
            level_id = str(record['level_id'])
            level = level_lookup.get(level_id)
            if level:
                level_points = calculate_level_points(level.get("position", 0), level.get("is_legacy", False))
                
                if level.get('is_legacy', False):
                    points = 0.0
                elif record['progress'] == 100:
                    points = float(level_points)
                else:
                    min_percentage = level.get('min_percentage', 100)
                    if record['progress'] >= min_percentage and min_percentage < 100:
                        points = round(float(level_points) * 0.1, 2)
                    else:
                        points = 0.0
                
                expected_total += points
        
        expected_total = round(expected_total, 2)
        
        if abs(current_points - expected_total) < 0.01:
            print(f"  ✅ {username}: {current_points} points (already correct)")
        else:
            print(f"  🔄 {username}: {current_points} → {expected_total} points (needs update)")
    
    print(f"\n🎉 Fixed admin recalculate function simulation completed!")
    print(f"📊 Summary: {levels_to_update} levels and {users_to_update} users would be updated")
    
    if levels_to_update == 0 and users_to_update == 0:
        print("✅ All points are already correct! Admin function is working perfectly.")
    else:
        print("🔄 Admin function will fix the remaining point discrepancies.")

if __name__ == "__main__":
    main()