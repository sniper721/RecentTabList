#!/usr/bin/env python3
"""
Find users with similar names
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
print("Connecting to MongoDB...")
mongo_client = MongoClient(mongodb_uri)
mongo_db = mongo_client[mongodb_db]

try:
    # Find users with "insane" in their name (case insensitive)
    users = list(mongo_db.users.find(
        {"username": {"$regex": "insane", "$options": "i"}},
        {"username": 1, "_id": 1}
    ))
    
    print(f"Found {len(users)} users with 'insane' in their username:")
    for user in users:
        print(f"  - {user['username']} (ID: {user['_id']})")
    
    # Also check for exact matches with different cases
    exact_matches = list(mongo_db.users.find(
        {"username": {"$regex": "^insaneI$", "$options": "i"}},
        {"username": 1, "_id": 1}
    ))
    
    print(f"\nExact matches for 'insaneI' (case insensitive):")
    for user in exact_matches:
        print(f"  - {user['username']} (ID: {user['_id']})")
        
    # Show all users if there are not too many
    total_users = mongo_db.users.count_documents({})
    print(f"\nTotal users in database: {total_users}")
    
    if total_users <= 20:
        print("\nAll users:")
        all_users = list(mongo_db.users.find({}, {"username": 1, "_id": 1}).sort("username", 1))
        for user in all_users:
            print(f"  - {user['username']}")

except Exception as e:
    print(f"Error: {e}")
finally:
    mongo_client.close()