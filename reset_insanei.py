#!/usr/bin/env python3
"""
Reset InsaneI's points and records completely
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime, timezone

# Load environment variables
load_dotenv()

# MongoDB configuration
mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

def reset_insanei_data():
    """Reset all of InsaneI's points and records"""
    print("🔧 Resetting InsaneI's data...")
    
    try:
        # Connect to MongoDB
        mongo_client = MongoClient(
            mongodb_uri,
            tls=True,
            tlsAllowInvalidCertificates=False,
            tlsAllowInvalidHostnames=False,
            serverSelectionTimeoutMS=60000,
            socketTimeoutMS=60000,
            connectTimeoutMS=30000,
            maxPoolSize=10,
            minPoolSize=1,
            maxIdleTimeMS=30000,
            waitQueueTimeoutMS=10000,
            retryWrites=True,
            retryReads=True
        )
        mongo_db = mongo_client[mongodb_db]
        
        # Test connection
        mongo_client.admin.command('ping', maxTimeMS=30000)
        print("✅ MongoDB connection successful")
        
        # Find InsaneI user (case insensitive)
        user = mongo_db.users.find_one({"username": {"$regex": "^insanei$", "$options": "i"}})
        
        if not user:
            print("❌ User 'InsaneI' not found")
            return False
        
        user_id = user['_id']
        username = user['username']
        print(f"✅ Found user: {username} (ID: {user_id})")
        
        # 1. Delete all records for this user
        records_result = mongo_db.records.delete_many({"user_id": user_id})
        print(f"🗑️  Deleted {records_result.deleted_count} records")
        
        # 2. Reset user points to 0
        points_result = mongo_db.users.update_one(
            {"_id": user_id},
            {"$set": {"points": 0.0}}
        )
        print(f"🔄 Reset points to 0 (modified: {points_result.modified_count})")
        
        # 3. Log the admin action
        admin_log = {
            "timestamp": datetime.now(timezone.utc),
            "admin_username": "System",
            "action": "RESET USER DATA",
            "target_user": username,
            "details": f"Reset all points and records for user {username}",
            "ip_address": "127.0.0.1"
        }
        mongo_db.admin_logs.insert_one(admin_log)
        print("📝 Logged admin action")
        
        # 4. Verify the reset
        updated_user = mongo_db.users.find_one({"_id": user_id})
        remaining_records = mongo_db.records.count_documents({"user_id": user_id})
        
        print(f"\n✅ Reset completed:")
        print(f"   - User points: {updated_user.get('points', 0)}")
        print(f"   - Remaining records: {remaining_records}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error resetting InsaneI's data: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚨 RESETTING INSANEI'S DATA")
    print("This will delete ALL records and reset points to 0")
    
    confirm = input("Are you sure? Type 'YES' to confirm: ")
    if confirm == "YES":
        success = reset_insanei_data()
        if success:
            print("\n✅ InsaneI's data reset successfully!")
        else:
            print("\n❌ Failed to reset InsaneI's data")
    else:
        print("❌ Reset cancelled")