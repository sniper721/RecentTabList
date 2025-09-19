#!/usr/bin/env python3
"""
Specifically fix InsaneI's points issue
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

def fix_insanei_points():
    """Fix points for InsaneI specifically"""
    print("🔧 Fixing InsaneI's points...")
    
    # Find InsaneI user
    user = mongo_db.users.find_one({"username": {"$regex": "^insanei$", "$options": "i"}})
    
    if not user:
        print("❌ User 'InsaneI' not found")
        return False
    
    print(f"Found user: {user['username']} (ID: {user['_id']})")
    print(f"Current points: {user.get('points', 0)}")
    
    # Get all approved records for this user
    records = list(mongo_db.records.find({
        "user_id": user['_id'], 
        "status": "approved"
    }))
    
    print(f"Found {len(records)} approved records")
    
    # Calculate total points manually
    total_points = 0
    for record in records:
        # Get level info
        level = mongo_db.levels.find_one({"_id": record['level_id']})
        if not level:
            print(f"❌ Level not found for record: {record['level_id']}")
            continue
            
        if level.get('is_legacy', False):
            continue  # Legacy levels don't give points
            
        # Calculate points
        if record['progress'] == 100:
            points = float(level.get('points', 0))
        else:
            min_percentage = level.get('min_percentage', 100)
            if record['progress'] >= min_percentage and min_percentage < 100:
                points = round(float(level.get('points', 0)) * 0.1, 2)
            else:
                points = 0
                
        total_points += points
        print(f"Level: {level['name']} (#{level['position']}) - Progress: {record['progress']}% = {points} points")
    
    print(f"Calculated total points: {total_points}")
    
    # Force update with direct MongoDB operation
    try:
        result = mongo_db.users.update_one(
            {"_id": user['_id']},
            {"$set": {"points": float(total_points)}},
            upsert=False
        )
        
        if result.modified_count > 0:
            print(f"✅ Successfully updated points for {user['username']}")
            
            # Verify the update
            updated_user = mongo_db.users.find_one({"_id": user['_id']})
            print(f"Verified points: {updated_user.get('points', 0)}")
            return True
        else:
            print(f"❌ No documents were modified. Matched: {result.matched_count}")
            
            # Try alternative approach - check if user exists
            user_check = mongo_db.users.find_one({"_id": user['_id']})
            if user_check:
                print(f"User exists with current points: {user_check.get('points', 0)}")
                
                # Try using string ID instead
                result2 = mongo_db.users.update_one(
                    {"username": user['username']},
                    {"$set": {"points": float(total_points)}}
                )
                
                if result2.modified_count > 0:
                    print(f"✅ Successfully updated points using username")
                    return True
                else:
                    print(f"❌ Still failed to update. Matched by username: {result2.matched_count}")
            
            return False
            
    except Exception as e:
        print(f"❌ Error updating points: {e}")
        return False

def main():
    """Main function"""
    try:
        # Test connection
        mongo_client.admin.command('ping')
        print("✅ MongoDB connection successful")
        
        # Fix InsaneI's points
        success = fix_insanei_points()
        
        if success:
            print("\n✅ InsaneI's points fixed successfully!")
        else:
            print("\n❌ Failed to fix InsaneI's points")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    finally:
        mongo_client.close()
    
    return True

if __name__ == "__main__":
    main()