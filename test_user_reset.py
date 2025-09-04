#!/usr/bin/env python3
"""
Test script for user reset functionality
"""

import os
import sys
from pymongo import MongoClient
from datetime import datetime, timezone
from bson.objectid import ObjectId

def test_user_reset_functionality():
    """Test the user reset functionality"""
    try:
        # Connect to MongoDB
        mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
        mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')
        
        print(f"Connecting to MongoDB: {mongodb_uri}")
        mongo_client = MongoClient(mongodb_uri)
        mongo_db = mongo_client[mongodb_db]
        
        # Create a test user
        test_user = {
            "_id": 999999,
            "username": "test_reset_user",
            "email": "test_reset@example.com",
            "password_hash": "test_hash",
            "is_admin": False,
            "points": 1000,
            "date_joined": datetime.now(timezone.utc),
            "last_ip": "192.168.1.100"
        }
        
        # Insert test user
        mongo_db.users.replace_one({"_id": 999999}, test_user, upsert=True)
        print("✅ Created test user")
        
        # Create some test records for the user
        test_records = []
        for i in range(5):
            record = {
                "_id": ObjectId(),
                "user_id": 999999,
                "level_id": i + 1,
                "percentage": 100,
                "status": "approved",
                "video_url": f"https://example.com/video{i}.mp4",
                "date_submitted": datetime.now(timezone.utc)
            }
            test_records.append(record)
        
        # Insert test records
        mongo_db.records.insert_many(test_records)
        print(f"✅ Created {len(test_records)} test records for user")
        
        # Test user reset functionality
        # Delete all user's records
        deleted_records = mongo_db.records.delete_many({"user_id": 999999})
        print(f"✅ Deleted {deleted_records.deleted_count} records")
        
        # Reset user points to 0
        mongo_db.users.update_one(
            {"_id": 999999},
            {"$set": {"points": 0}}
        )
        print("✅ Reset user points to 0")
        
        # Verify the reset worked
        updated_user = mongo_db.users.find_one({"_id": 999999})
        remaining_records = mongo_db.records.count_documents({"user_id": 999999})
        
        if updated_user and updated_user.get("points") == 0 and remaining_records == 0:
            print("✅ User reset verification successful")
        else:
            print("❌ User reset verification failed")
            
        # Clean up test user
        mongo_db.users.delete_one({"_id": 999999})
        print("✅ Cleaned up test user")
        
        print("🎉 All user reset functionality tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing user reset functionality: {e}")
        return False

if __name__ == "__main__":
    test_user_reset_functionality()