#!/usr/bin/env python3
"""
Update all level points using the demonlist formula
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def calculate_level_points(position, is_legacy=False, level_type="Level"):
    """Calculate points based on position using demonlist formula"""
    if is_legacy:
        return 0
    
    if position == 1:
        return 400
    elif position <= 20:
        # Linear decrease from 360 to 40
        return int((90 - (position - 2) * (80 / 18)) * 4)
    elif position <= 100:
        # Exponential decay from 40 to 5.2
        return max(5.2, 10 * (0.95 ** (position - 20)) * 4)
    else:
        return 5.2

def main():
    # MongoDB configuration
    mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
    mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')
    
    try:
        mongo_client = MongoClient(
            mongodb_uri,
            tls=True,
            tlsAllowInvalidCertificates=True,
            tlsAllowInvalidHostnames=True,
            serverSelectionTimeoutMS=5000
        )
        mongo_db = mongo_client[mongodb_db]
        
        # Get all levels
        levels = list(mongo_db.levels.find())
        
        print(f"Updating points for {len(levels)} levels...")
        
        for level in levels:
            old_points = level.get('points', 0)
            new_points = calculate_level_points(level['position'], level.get('is_legacy', False))
            
            if abs(old_points - new_points) > 0.01:
                mongo_db.levels.update_one(
                    {"_id": level['_id']},
                    {"$set": {"points": new_points}}
                )
                print(f"Level #{level['position']} '{level['name']}': {old_points} -> {new_points}")
        
        print("Points update completed!")
        
        # Recalculate all user points
        print("Recalculating user points...")
        users = list(mongo_db.users.find())
        
        for user in users:
            records = list(mongo_db.records.find({"user_id": user['_id'], "status": "approved"}))
            total_points = 0
            
            for record in records:
                level = mongo_db.levels.find_one({"_id": record['level_id']})
                if level and not level.get('is_legacy', False):
                    if record['progress'] == 100:
                        total_points += level['points']
                    elif record['progress'] >= level.get('min_percentage', 100):
                        total_points += level['points'] * 0.1
            
            mongo_db.users.update_one(
                {"_id": user['_id']},
                {"$set": {"points": total_points}}
            )
            print(f"User '{user['username']}': {total_points} points")
        
        print("User points recalculation completed!")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()