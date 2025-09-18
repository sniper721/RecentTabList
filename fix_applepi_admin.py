#!/usr/bin/env python3
"""
Quick script to check and fix ApplePi's admin status
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB configuration
mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

def main():
    try:
        # Connect to MongoDB
        print("Connecting to MongoDB...")
        mongo_client = MongoClient(mongodb_uri)
        mongo_db = mongo_client[mongodb_db]
        
        # Test connection
        mongo_client.admin.command('ping')
        print("✓ Connected to MongoDB successfully")
        
        # Check ApplePi's current status
        username = "ipodnicks"  # ApplePi's actual username
        user = mongo_db.users.find_one({"username": username})
        
        if not user:
            print(f"❌ User '{username}' not found in database")
            return
        
        print(f"\n📋 Current status for {username}:")
        print(f"  User ID: {user['_id']}")
        print(f"  Username: {user['username']}")
        print(f"  is_admin: {user.get('is_admin', False)}")
        print(f"  head_admin: {user.get('head_admin', False)}")
        print(f"  Points: {user.get('points', 0)}")
        
        # Check if already admin
        if user.get('is_admin'):
            print(f"✅ {username} is already an admin")
        else:
            print(f"❌ {username} is NOT an admin")
            
            # Fix admin status
            response = input(f"\nDo you want to make {username} an admin? (y/n): ")
            if response.lower() == 'y':
                mongo_db.users.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"is_admin": True}}
                )
                print(f"✅ {username} has been promoted to admin")
                print("⚠️  User must log out and log back in to see admin panel")
            else:
                print("❌ No changes made")
        
        # Also check if there are any other users with similar names
        print(f"\n🔍 Checking for similar usernames...")
        similar_users = list(mongo_db.users.find(
            {"username": {"$regex": "apple|ipod", "$options": "i"}},
            {"username": 1, "is_admin": 1, "head_admin": 1}
        ))
        
        if similar_users:
            print("Found similar users:")
            for similar_user in similar_users:
                admin_status = ""
                if similar_user.get('head_admin'):
                    admin_status = " [HEAD ADMIN]"
                elif similar_user.get('is_admin'):
                    admin_status = " [ADMIN]"
                print(f"  {similar_user['username']} (ID: {similar_user['_id']}){admin_status}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()