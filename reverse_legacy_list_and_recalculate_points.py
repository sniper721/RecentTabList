#!/usr/bin/env python3
"""
Script to reverse legacy list placements and recalculate all user points.

Changes:
1. Reverse legacy list placements (151→101, 152→102, ..., 274→224)
2. Recalculate all user points based on new positions
3. Update the points system to use the correct formula
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv
import time

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
    print("🔄 Starting legacy list reversal and points recalculation...")
    start_time = time.time()
    
    # Connect to MongoDB
    try:
        mongo_client = MongoClient(
            mongodb_uri,
            tls=True,
            tlsAllowInvalidCertificates=True,
            tlsAllowInvalidHostnames=True,
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
    
    # 1. Reverse legacy list placements
    print("\n1️⃣ Reversing legacy list placements...")
    
    # Get all legacy levels sorted by current position
    legacy_levels = list(mongo_db.levels.find({'is_legacy': True}).sort('position', 1))
    print(f"Found {len(legacy_levels)} legacy levels")
    
    if not legacy_levels:
        print("❌ No legacy levels found!")
        return
    
    # Calculate new positions (reverse order)
    # Current positions: 151, 152, 153, ..., 274
    # New positions:    101, 102, 103, ..., 224
    current_positions = [level['position'] for level in legacy_levels]
    current_positions.sort()
    
    # Create mapping: old_position -> new_position
    position_mapping = {}
    for i, old_pos in enumerate(current_positions):
        new_pos = 101 + i
        position_mapping[old_pos] = new_pos
    
    print(f"Position mapping created:")
    print(f"  First level: #{current_positions[0]} → #{position_mapping[current_positions[0]]}")
    print(f"  Last level:  #{current_positions[-1]} → #{position_mapping[current_positions[-1]]}")
    
    # Update legacy levels with new positions
    updated_levels = 0
    for level in legacy_levels:
        old_position = level['position']
        new_position = position_mapping[old_position]
        
        # Update the level
        result = mongo_db.levels.update_one(
            {'_id': level['_id']},
            {'$set': {'position': new_position}}
        )
        
        if result.modified_count > 0:
            updated_levels += 1
            print(f"  ✅ {level['name']}: #{old_position} → #{new_position}")
    
    print(f"✅ Updated {updated_levels} legacy levels")
    
    # 2. Recalculate all level points based on new positions
    print("\n2️⃣ Recalculating all level points...")
    
    # Get all levels (both main and legacy)
    all_levels = list(mongo_db.levels.find())
    levels_updated = 0
    
    for level in all_levels:
        new_points = calculate_level_points(level['position'], level.get('is_legacy', False))
        old_points = level.get('points', 0)
        
        # Update if points changed
        if abs(new_points - old_points) > 0.01:
            result = mongo_db.levels.update_one(
                {'_id': level['_id']},
                {'$set': {'points': new_points}}
            )
            
            if result.modified_count > 0:
                levels_updated += 1
                if level.get('is_legacy', False):
                    print(f"  🔄 Legacy {level['name']}: #{level['position']} - {old_points} → {new_points} points")
                else:
                    print(f"  🔄 Main {level['name']}: #{level['position']} - {old_points} → {new_points} points")
    
    print(f"✅ Updated points for {levels_updated} levels")
    
    # 3. Recalculate all user points
    print("\n3️⃣ Recalculating all user points...")
    
    # Get all users
    users = list(mongo_db.users.find())
    print(f"Found {len(users)} users")
    
    # Create level lookup for quick access
    level_lookup = {}
    all_levels = list(mongo_db.levels.find())
    for level in all_levels:
        level_lookup[str(level['_id'])] = level
    
    users_updated = 0
    total_points_recalculated = 0
    
    for user in users:
        username = user.get('username', 'Unknown')
        user_id = user['_id']
        
        # Get user's records
        records = list(mongo_db.records.find({'user_id': user_id}))
        
        # Calculate expected total points
        expected_total = 0.0
        for record in records:
            level_id = str(record['level_id'])
            level = level_lookup.get(level_id)
            if level:
                points_earned = calculate_record_points(record, level)
                expected_total += points_earned
        
        expected_total = round(expected_total, 2)
        current_points = round(user.get('points', 0), 2)
        
        # Update if points don't match
        if abs(current_points - expected_total) > 0.01:
            result = mongo_db.users.update_one(
                {'_id': user_id},
                {'$set': {'points': expected_total}}
            )
            
            if result.modified_count > 0:
                users_updated += 1
                total_points_recalculated += abs(expected_total - current_points)
                print(f"  🔄 {username}: {current_points} → {expected_total} points")
    
    print(f"✅ Updated points for {users_updated} users")
    print(f"📈 Total points recalculated: {total_points_recalculated:.2f}")
    
    # 4. Verification
    print("\n4️⃣ Verifying changes...")
    
    # Check legacy list positions
    final_legacy = list(mongo_db.levels.find({'is_legacy': True}).sort('position', 1))
    print(f"Legacy list now has positions: #{final_legacy[0]['position']} to #{final_legacy[-1]['position']}")
    
    # Check points for some key positions
    test_positions = [1, 50, 100, 101, 150, 224]
    print(f"\nPoints verification:")
    for pos in test_positions:
        level = mongo_db.levels.find_one({'position': pos})
        if level:
            points = level.get('points', 0)
            status = "Legacy" if level.get('is_legacy') else "Main"
            print(f"  #{pos} ({status}): {points} points")
    
    # Final summary
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"\n🎉 COMPLETED!")
    print(f"✅ Legacy list reversed: {len(legacy_levels)} levels")
    print(f"✅ Level points recalculated: {levels_updated} levels")
    print(f"✅ User points recalculated: {users_updated} users")
    print(f"⏱️  Total time: {duration:.2f} seconds")
    
    print(f"\n📋 NEW LEGACY LIST STRUCTURE:")
    print(f"  - Positions now range from #101 to #{100 + len(legacy_levels)}")
    print(f"  - First legacy level: {final_legacy[0]['name']} at #{final_legacy[0]['position']}")
    print(f"  - Last legacy level: {final_legacy[-1]['name']} at #{final_legacy[-1]['position']}")
    print(f"  - All points recalculated using formula: p = 250(0.965)^(x-1)")

if __name__ == "__main__":
    main()