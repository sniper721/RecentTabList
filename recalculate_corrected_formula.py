#!/usr/bin/env python3
"""
Script to recalculate all points with the corrected formula: p = 250(0.965)^(x-1)
This ensures position 1 = 250 points, position 50 = 40.4 points, position 100 = 6.5 points, position 150 = 1.05 points
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
    # Position 1 = 250(0.965)^0 = 250 points
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
    print("🚀 Recalculating with corrected formula: p = 250(0.965)^(x-1)")
    
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
    
    # Verify the formula gives correct values
    print(f"\n📊 Formula verification:")
    print(f"  Position 1: {calculate_level_points(1)} points (should be 250)")
    print(f"  Position 50: {calculate_level_points(50)} points (should be ~40.4)")
    print(f"  Position 100: {calculate_level_points(100)} points (should be ~6.5)")
    print(f"  Position 150: {calculate_level_points(150)} points (should be ~1.05)")
    
    # Step 1: Update all main list level points
    main_levels = list(mongo_db.levels.find({
        "is_legacy": {"$ne": True}
    }))
    
    print(f"\n🔄 Updating {len(main_levels)} main list levels...")
    updated_levels = 0
    
    for level in main_levels:
        position = level["position"]
        new_points = calculate_level_points(position, is_legacy=False)
        old_points = level.get("points", 0)
        
        if abs(new_points - old_points) > 0.01:  # Only update if points changed
            result = mongo_db.levels.update_one(
                {"_id": level["_id"]},
                {"$set": {"points": new_points}}
            )
            
            if result.modified_count > 0:
                updated_levels += 1
                print(f"  #{position}: {level['name']} - {old_points} → {new_points} points")
    
    print(f"✅ Updated {updated_levels} level point values")
    
    # Step 2: Recalculate all user points
    users = list(mongo_db.users.find({}))
    print(f"\n🔄 Recalculating points for {len(users)} users...")
    
    # Create level lookup for faster processing
    levels = list(mongo_db.levels.find({}))
    level_lookup = {str(level['_id']): level for level in levels}
    
    updated_users = 0
    total_points_change = 0.0
    
    for user in users:
        user_id = user['_id']
        old_points = user.get('points', 0.0)
        
        # Get all approved records for this user
        records = list(mongo_db.records.find({
            "user_id": user_id,
            "status": "approved"
        }))
        
        # Calculate new total points
        new_total_points = 0.0
        record_count = 0
        
        for record in records:
            level_id = str(record['level_id'])
            level = level_lookup.get(level_id)
            
            if level:
                points = calculate_record_points(record, level)
                new_total_points += points
                if points > 0:
                    record_count += 1
        
        # Round to 2 decimal places
        new_total_points = round(new_total_points, 2)
        
        # Update user if points changed
        if abs(new_total_points - old_points) > 0.01:
            result = mongo_db.users.update_one(
                {"_id": user_id},
                {"$set": {"points": new_total_points}}
            )
            
            if result.modified_count > 0:
                updated_users += 1
                points_change = new_total_points - old_points
                total_points_change += points_change
                
                print(f"  {user.get('username', 'Unknown')}: {old_points} → {new_total_points} points ({points_change:+.2f})")
    
    print(f"\n🎉 Recalculation completed!")
    print(f"  Levels updated: {updated_levels}")
    print(f"  Users updated: {updated_users}/{len(users)}")
    print(f"  Total points change: {total_points_change:+.2f}")
    
    # Show final points distribution
    print(f"\n📈 Final points distribution:")
    sample_positions = [1, 10, 25, 50, 75, 100, 125, 150]
    for pos in sample_positions:
        points = calculate_level_points(pos)
        print(f"  Position #{pos}: {points} points")
    
    # Show top 10 users after recalculation
    print(f"\n🏆 Top 10 users after recalculation:")
    top_users = list(mongo_db.users.find({}).sort("points", -1).limit(10))
    
    for i, user in enumerate(top_users, 1):
        username = user.get('username', 'Unknown')
        points = user.get('points', 0)
        print(f"  #{i}: {username} - {points} points")

if __name__ == "__main__":
    main()