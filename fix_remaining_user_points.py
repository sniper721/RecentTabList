#!/usr/bin/env python3
"""
Fix the remaining 4 users with incorrect points
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
    print("🔧 Fixing remaining user points...")
    
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
    
    # Get level lookup
    levels = list(mongo_db.levels.find({}))
    level_lookup = {str(level['_id']): level for level in levels}
    
    # Target users that need fixing
    target_users = ['InsaneI', 'oblivionusreal', 'ApplePi', 'Scorch', 'Kye']
    
    users_fixed = 0
    
    for username in target_users:
        user = mongo_db.users.find_one({"username": username})
        if not user:
            print(f"⚠️  User {username} not found")
            continue
        
        user_id = user['_id']
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
                
                correct_total_points += points
        
        # Round to 2 decimal places
        correct_total_points = round(correct_total_points, 2)
        
        # Update user if points are incorrect
        if abs(correct_total_points - current_points) > 0.01:
            result = mongo_db.users.update_one(
                {"_id": user_id},
                {"$set": {"points": correct_total_points}}
            )
            
            if result.modified_count > 0:
                users_fixed += 1
                print(f"✅ Fixed {username}: {current_points} → {correct_total_points} points")
            else:
                print(f"❌ Failed to fix {username}")
        else:
            print(f"✅ {username}: {current_points} points (already correct)")
    
    print(f"\n🎉 Fixed {users_fixed} users!")
    
    # Final verification
    print(f"\n🔍 Final verification of top 5 users:")
    top_users = list(mongo_db.users.find({}).sort("points", -1).limit(5))
    
    for i, user in enumerate(top_users, 1):
        username = user.get('username', 'Unknown')
        points = user.get('points', 0)
        print(f"  #{i}: {username} - {points} points")

if __name__ == "__main__":
    main()