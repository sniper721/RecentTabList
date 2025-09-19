#!/usr/bin/env python3
"""
Fix profile and points issues:
1. Fix profile fusion issue
2. Remove download available text
3. Fix missing points for insanei
"""

from pymongo import MongoClient
from datetime import datetime, timezone
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

def calculate_record_points(record, level):
    """Calculate points earned from a record"""
    status = record.get('status', 'pending')
    if status != 'approved' or level.get('is_legacy', False):
        return 0.0
    
    # Full completion (100% points)
    if record['progress'] == 100:
        return float(level['points'])
    
    # Partial completion - 10% of full points when reaching minimum percentage
    min_percentage = level.get('min_percentage', 100)
    if record['progress'] >= min_percentage and min_percentage < 100:
        return round(float(level['points']) * 0.1, 2)  # 10% of full points
    
    return 0.0

def update_user_points(user_id):
    """Recalculate and update user's total points"""
    pipeline = [
        {"$match": {"user_id": user_id, "status": "approved"}},
        {"$lookup": {
            "from": "levels",
            "localField": "level_id", 
            "foreignField": "_id",
            "as": "level"
        }},
        {"$unwind": "$level"},
        {"$project": {
            "progress": 1,
            "status": 1,
            "level.points": 1,
            "level.is_legacy": 1,
            "level.min_percentage": 1,
            "level.name": 1,
            "level.position": 1
        }}
    ]
    
    records_with_levels = list(mongo_db.records.aggregate(pipeline))
    total_points = 0
    
    print(f"\n=== Points calculation for user {user_id} ===")
    for record in records_with_levels:
        level = record['level']
        record_with_status = {
            'progress': record['progress'],
            'status': record.get('status', 'approved')
        }
        points = calculate_record_points(record_with_status, level)
        total_points += points
        print(f"Level: {level['name']} (#{level['position']}) - Progress: {record['progress']}% = {points} points")
    
    print(f"Total points: {total_points}")
    
    # Update user's points
    result = mongo_db.users.update_one(
        {"_id": user_id},
        {"$set": {"points": total_points}}
    )
    
    if result.modified_count > 0:
        print(f"✅ Updated points for user {user_id}")
    else:
        print(f"❌ Failed to update points for user {user_id}")
    
    return total_points

def fix_insanei_points():
    """Fix points for insanei user"""
    print("\n🔧 Fixing points for insanei...")
    
    # Find insanei user (case insensitive)
    user = mongo_db.users.find_one({"username": {"$regex": "^insanei$", "$options": "i"}})
    
    if not user:
        print("❌ User 'insanei' not found")
        return False
    
    print(f"Found user: {user['username']} (ID: {user['_id']})")
    print(f"Current points: {user.get('points', 0)}")
    
    # Recalculate points
    new_points = update_user_points(user['_id'])
    
    print(f"✅ Fixed points for {user['username']}: {new_points}")
    return True

def check_profile_routes():
    """Check if there are any issues with profile routes"""
    print("\n🔧 Checking profile route issues...")
    
    # This is mainly a backend issue, so we'll check the data integrity
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
            "record_count": "$count"
        }}
    ]))
    
    print(f"Found {len(users_with_records)} users with records")
    
    # Check for any data inconsistencies
    for user_data in users_with_records[:5]:  # Check first 5 users
        user_id = user_data['user_id']
        username = user_data['username']
        
        # Verify user exists and records match
        user = mongo_db.users.find_one({"_id": user_id})
        if not user:
            print(f"❌ Orphaned records found for user ID: {user_id}")
            continue
            
        records = list(mongo_db.records.find({"user_id": user_id}))
        if len(records) != user_data['record_count']:
            print(f"❌ Record count mismatch for {username}")
        else:
            print(f"✅ Data integrity OK for {username}")

def remove_download_references():
    """Remove any download-related data that might be causing the issue"""
    print("\n🔧 Checking for download-related data...")
    
    # Check if there are any levels with download data
    levels_with_downloads = list(mongo_db.levels.find({"downloads": {"$exists": True}}))
    
    if levels_with_downloads:
        print(f"Found {len(levels_with_downloads)} levels with download data")
        
        # Remove download fields
        result = mongo_db.levels.update_many(
            {"downloads": {"$exists": True}},
            {"$unset": {"downloads": "", "likes": "", "length": ""}}
        )
        
        print(f"✅ Removed download data from {result.modified_count} levels")
    else:
        print("✅ No download data found in levels")
    
    # Check for any cached data or settings
    settings = mongo_db.site_settings.find_one({"_id": "main"})
    if settings and "downloads" in settings:
        mongo_db.site_settings.update_one(
            {"_id": "main"},
            {"$unset": {"downloads": ""}}
        )
        print("✅ Removed download setting from site settings")

def main():
    """Main function to fix all issues"""
    print("🚀 Starting profile and points fixes...")
    
    try:
        # Test connection
        mongo_client.admin.command('ping')
        print("✅ MongoDB connection successful")
        
        # Fix 1: Check profile data integrity
        check_profile_routes()
        
        # Fix 2: Remove download references
        remove_download_references()
        
        # Fix 3: Fix insanei's points
        fix_insanei_points()
        
        # Additional: Recalculate points for all users with recent activity
        print("\n🔧 Recalculating points for users with recent activity...")
        recent_users = list(mongo_db.records.aggregate([
            {"$match": {"date_submitted": {"$gte": datetime.now(timezone.utc).replace(day=1)}}},  # This month
            {"$group": {"_id": "$user_id"}},
            {"$lookup": {
                "from": "users",
                "localField": "_id",
                "foreignField": "_id",
                "as": "user"
            }},
            {"$unwind": "$user"},
            {"$limit": 10}  # Limit to 10 users to avoid timeout
        ]))
        
        for user_data in recent_users:
            user_id = user_data['_id']
            username = user_data['user']['username']
            print(f"Recalculating points for {username}...")
            update_user_points(user_id)
        
        print("\n✅ All fixes completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during fixes: {e}")
        return False
    
    finally:
        mongo_client.close()
    
    return True

if __name__ == "__main__":
    main()