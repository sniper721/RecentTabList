#!/usr/bin/env python3
"""
Script to recalculate all level points and user points with the new formula
where position 100 = 6.4 points
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
    """Calculate points based on position using new exponential formula"""
    if is_legacy:
        return 0.0
    # p = 250(0.963655)^(x-1) where x is the placement of the level on the list
    # Position 1 = 250(0.963655)^0 = 250 points
    # Position 100 = 250(0.963655)^99 = 6.4 points
    return round(250 * (0.9636550814213581 ** (position - 1)), 2)

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
    print("Connecting to MongoDB...")
    client = MongoClient(mongodb_uri)
    db = client[mongodb_db]
    
    print("Updating level points with new formula...")
    
    # Update main list levels
    main_levels = list(db.levels.find({"is_legacy": {"$ne": True}}).sort("position", 1))
    updated_levels = 0
    
    for level in main_levels:
        position = level.get('position')
        if position:
            new_points = calculate_level_points(position, False)
            old_points = level.get('points', 0)
            
            if abs(new_points - old_points) > 0.01:  # Only update if significantly different
                db.levels.update_one(
                    {"_id": level["_id"]},
                    {"$set": {"points": new_points}}
                )
                print(f"Level {level.get('name', 'Unknown')} (#{position}): {old_points} → {new_points} points")
                updated_levels += 1
    
    print(f"\n✓ Updated {updated_levels} level points")
    
    # Update legacy levels to 0 points
    legacy_levels = list(db.levels.find({"is_legacy": True}))
    for level in legacy_levels:
        if level.get('points', 0) != 0:
            db.levels.update_one(
                {"_id": level["_id"]},
                {"$set": {"points": 0}}
            )
            print(f"Set legacy level {level.get('name', 'Unknown')} to 0 points")
    
    print("Recalculating user points...")
    
    # Get all users
    users = list(db.users.find({}))
    updated_users = 0
    
    for user in users:
        total_points = 0.0
        user_records = list(db.records.find({"user_id": user["_id"], "status": "approved"}))
        
        # Calculate points from records
        for record in user_records:
            level = db.levels.find_one({"_id": record["level_id"]})
            if level:
                record_points = calculate_record_points(record, level)
                total_points += record_points
        
        # Update user's total points
        old_points = user.get('points', 0)
        if abs(total_points - old_points) > 0.01:  # Only update if significantly different
            db.users.update_one(
                {"_id": user["_id"]},
                {"$set": {"points": round(total_points, 2)}}
            )
            print(f"User {user.get('username', 'Unknown')}: {old_points} → {round(total_points, 2)} points")
            updated_users += 1
    
    print(f"\n✓ Recalculated points for {updated_users} users")
    print("✓ All points updated successfully!")
    
    # Show some key position examples
    print("\nKey position examples with new formula:")
    for pos in [1, 10, 25, 50, 75, 100, 125, 150]:
        points = calculate_level_points(pos)
        print(f"Position #{pos}: {points} points")

if __name__ == "__main__":
    main()