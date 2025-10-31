#!/usr/bin/env python3
"""
Update points formula to new system where:
- Position 1 = 250 points
- Position 150 = 1 point
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
    # p = 250(0.9636)^(x-1) where x is the placement of the level on the list
    # Position 1 = 250(0.9636)^0 = 250 points
    # Position 150 = 250(0.9636)^149 ≈ 1 point
    return round(250 * (0.9636214148582346 ** (position - 1)), 2)

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
            
            if new_points != old_points:
                db.levels.update_one(
                    {"_id": level["_id"]},
                    {"$set": {"points": new_points}}
                )
                print(f"Level '{level['name']}' (pos {position}): {old_points} → {new_points} points")
                updated_levels += 1
    
    print(f"\nUpdated {updated_levels} levels with new points formula")
    
    # Now recalculate all user points
    print("\nRecalculating all user points...")
    
    users = list(db.users.find())
    updated_users = 0
    
    for user in users:
        user_id = user["_id"]
        
        # Get all approved records for this user
        records = list(db.records.find({
            "user_id": user_id,
            "status": "approved"
        }))
        
        total_points = 0.0
        
        for record in records:
            level = db.levels.find_one({"_id": record["level_id"]})
            if level and not level.get('is_legacy', False):
                # Full completion gets full points
                if record['progress'] == 100:
                    total_points += float(level['points'])
                # Partial completion gets 10% of points if above minimum
                elif record['progress'] >= level.get('min_percentage', 100) and level.get('min_percentage', 100) < 100:
                    total_points += round(float(level['points']) * 0.1, 2)
        
        total_points = round(total_points, 2)
        old_points = user.get('points', 0)
        
        if total_points != old_points:
            db.users.update_one(
                {"_id": user_id},
                {"$set": {"points": total_points}}
            )
            print(f"User '{user['username']}': {old_points} → {total_points} points")
            updated_users += 1
    
    print(f"\nUpdated {updated_users} users with recalculated points")
    print("Points formula update complete!")
    
    # Show some examples
    print("\nNew points distribution examples:")
    for pos in [1, 10, 25, 50, 75, 100, 125, 150]:
        points = calculate_level_points(pos)
        print(f"Position {pos}: {points} points")

if __name__ == "__main__":
    main()