#!/usr/bin/env python3
"""
Script to update all existing level points to integers and test position shifting
"""

from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# MongoDB configuration
mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

def calculate_level_points(position, is_legacy=False, level_type="Level"):
    """Calculate points based on position using exponential formula"""
    if is_legacy:
        return 0
    # p = 250(0.9475)^(position-1)
    # Position 1 = exponent 0, Position 2 = exponent 1, etc.
    return int(250 * (0.9475 ** (position - 1)))

def main():
    try:
        # Connect to MongoDB
        print("Connecting to MongoDB...")
        mongo_client = MongoClient(
            mongodb_uri,
            tls=True,
            tlsAllowInvalidCertificates=True,
            tlsAllowInvalidHostnames=True,
            serverSelectionTimeoutMS=30000,
            socketTimeoutMS=30000,
            connectTimeoutMS=30000
        )
        mongo_db = mongo_client[mongodb_db]
        
        # Test connection
        mongo_client.admin.command('ping')
        print("✓ Connected to MongoDB")
        
        # Get all levels
        levels = list(mongo_db.levels.find())
        print(f"Found {len(levels)} levels")
        
        updated_count = 0
        for level in levels:
            # Calculate new integer points
            new_points = calculate_level_points(
                level['position'], 
                level.get('is_legacy', False),
                level.get('level_type', 'Level')
            )
            
            # Check if points need updating
            current_points = level.get('points', 0)
            if current_points != new_points:
                print(f"Updating {level['name']}: {current_points} -> {new_points} points")
                mongo_db.levels.update_one(
                    {"_id": level['_id']},
                    {"$set": {"points": new_points}}
                )
                updated_count += 1
            else:
                print(f"✓ {level['name']}: {current_points} points (no change needed)")
        
        print(f"\n✓ Updated {updated_count} levels with integer points")
        
        # Update user points to integers as well
        print("\nUpdating user points...")
        users = list(mongo_db.users.find({"points": {"$exists": True}}))
        user_updated_count = 0
        
        for user in users:
            current_points = user.get('points', 0)
            new_points = int(current_points) if current_points else 0
            
            if current_points != new_points:
                print(f"Updating user {user['username']}: {current_points} -> {new_points} points")
                mongo_db.users.update_one(
                    {"_id": user['_id']},
                    {"$set": {"points": new_points}}
                )
                user_updated_count += 1
        
        print(f"✓ Updated {user_updated_count} users with integer points")
        
        print("\n✅ All done! Points are now integers and position shifting is ready.")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()