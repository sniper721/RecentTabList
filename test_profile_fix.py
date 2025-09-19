#!/usr/bin/env python3
"""
Test the profile fix to see if the issue is resolved
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB configuration
mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

# Initialize MongoDB
print("Connecting to MongoDB...")
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

def test_profile_data():
    """Test profile data integrity"""
    print("🔍 Testing profile data...")
    
    # Get a few users with records
    users_with_records = list(mongo_db.records.aggregate([
        {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
        {"$lookup": {
            "from": "users",
            "localField": "_id",
            "foreignField": "_id",
            "as": "user"
        }},
        {"$unwind": "$user"},
        {"$project": {
            "user_id": "$_id",
            "username": "$user.username",
            "record_count": "$count",
            "points": "$user.points"
        }},
        {"$limit": 5}
    ]))
    
    print(f"Found {len(users_with_records)} users with records:")
    
    for user_data in users_with_records:
        user_id = user_data['user_id']
        username = user_data['username']
        record_count = user_data['record_count']
        points = user_data.get('points', 0)
        
        print(f"  - {username} (ID: {user_id}): {record_count} records, {points} points")
        
        # Test getting records for this user (simulating public profile)
        user_records = list(mongo_db.records.aggregate([
            {"$match": {"user_id": user_id, "status": "approved"}},
            {"$lookup": {
                "from": "levels",
                "localField": "level_id",
                "foreignField": "_id",
                "as": "level"
            }},
            {"$unwind": "$level"},
            {"$sort": {"date_submitted": -1}},
            {"$limit": 5}
        ]))
        
        print(f"    Recent approved records: {len(user_records)}")
        for record in user_records[:2]:  # Show first 2
            level_name = record['level']['name']
            progress = record['progress']
            print(f"      - {level_name}: {progress}%")

def check_insanei_specifically():
    """Check InsaneI's data specifically"""
    print("\n🔍 Checking InsaneI specifically...")
    
    user = mongo_db.users.find_one({"username": {"$regex": "^insanei$", "$options": "i"}})
    if not user:
        print("❌ InsaneI not found")
        return
    
    print(f"User: {user['username']} (ID: {user['_id']})")
    print(f"Points: {user.get('points', 0)}")
    
    # Get approved records
    approved_records = list(mongo_db.records.find({
        "user_id": user['_id'],
        "status": "approved"
    }))
    
    print(f"Approved records: {len(approved_records)}")
    
    # Get pending records
    pending_records = list(mongo_db.records.find({
        "user_id": user['_id'],
        "status": "pending"
    }))
    
    print(f"Pending records: {len(pending_records)}")
    
    # Check for any recently approved records that might not have been counted
    recent_approved = list(mongo_db.records.find({
        "user_id": user['_id'],
        "status": "approved"
    }).sort("date_submitted", -1).limit(5))
    
    print("Recent approved records:")
    for record in recent_approved:
        level = mongo_db.levels.find_one({"_id": record['level_id']})
        level_name = level['name'] if level else f"Level {record['level_id']}"
        print(f"  - {level_name}: {record['progress']}% (submitted: {record.get('date_submitted', 'Unknown')})")

def main():
    """Main function"""
    try:
        # Test connection
        mongo_client.admin.command('ping')
        print("✅ MongoDB connection successful")
        
        # Test profile data
        test_profile_data()
        
        # Check InsaneI specifically
        check_insanei_specifically()
        
        print("\n✅ Profile test completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    finally:
        mongo_client.close()
    
    return True

if __name__ == "__main__":
    main()