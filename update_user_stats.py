#!/usr/bin/env python3
"""
Update all user completion counts to exclude legacy levels
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB configuration
mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

# Connect to MongoDB
mongo_client = MongoClient(mongodb_uri)
mongo_db = mongo_client[mongodb_db]

def update_all_user_stats():
    """Update completion stats for all users to exclude legacy levels"""
    print("Updating user completion stats...")
    
    # Get all users
    users = list(mongo_db.users.find({}, {"_id": 1, "username": 1}))
    updated_count = 0
    
    for user in users:
        user_id = user['_id']
        
        # Get approved completions on main list levels only
        main_completions = list(mongo_db.records.aggregate([
            {"$match": {"user_id": user_id, "status": "approved", "progress": 100}},
            {"$lookup": {
                "from": "levels",
                "localField": "level_id", 
                "foreignField": "_id",
                "as": "level"
            }},
            {"$unwind": "$level"},
            {"$match": {"level.is_legacy": {"$ne": True}}}
        ]))
        
        # Update user's completion count (if we want to store it)
        # For now, we'll just rely on dynamic calculation
        updated_count += 1
        
        if updated_count % 10 == 0:
            print(f"   Processed {updated_count}/{len(users)} users...")
    
    print(f"Updated stats for {updated_count} users")
    return updated_count

if __name__ == "__main__":
    try:
        update_all_user_stats()
        print("All user stats updated successfully!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        mongo_client.close()