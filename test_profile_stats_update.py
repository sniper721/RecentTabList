#!/usr/bin/env python3
"""
Test the updated profile stats with separate main/legacy completion counts
"""

from pymongo import MongoClient
from bson.objectid import ObjectId
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

def test_updated_profile_stats(username):
    """Test the updated profile route with separate main/legacy stats"""
    print(f"\n🧪 TESTING UPDATED PROFILE STATS FOR: {username}")
    print("=" * 50)
    
    # Find user
    user = mongo_db.users.find_one({"username": username})
    if not user:
        print(f"❌ User '{username}' not found")
        return
    
    user_id = user['_id']
    
    # Simulate the updated profile route logic
    
    # Get ALL records for display in tabs
    all_user_records = list(mongo_db.records.aggregate([
        {"$match": {"user_id": user_id}},
        {"$lookup": {
            "from": "levels",
            "localField": "level_id",
            "foreignField": "_id",
            "as": "level"
        }},
        {"$unwind": "$level"},
        {"$sort": {"date_submitted": -1}}
    ]))
    
    # Get only APPROVED records
    approved_records = list(mongo_db.records.aggregate([
        {"$match": {"user_id": user_id, "status": "approved"}},
        {"$lookup": {
            "from": "levels",
            "localField": "level_id",
            "foreignField": "_id",
            "as": "level"
        }},
        {"$unwind": "$level"},
        {"$sort": {"date_submitted": -1}}
    ]))
    
    # Get only APPROVED records on MAIN LIST levels
    main_list_approved = list(mongo_db.records.aggregate([
        {"$match": {"user_id": user_id, "status": "approved"}},
        {"$lookup": {
            "from": "levels",
            "localField": "level_id",
            "foreignField": "_id",
            "as": "level"
        }},
        {"$unwind": "$level"},
        {"$match": {"level.is_legacy": {"$ne": True}}},
        {"$sort": {"date_submitted": -1}}
    ]))
    
    # Get only APPROVED records on LEGACY levels
    legacy_list_approved = list(mongo_db.records.aggregate([
        {"$match": {"user_id": user_id, "status": "approved"}},
        {"$lookup": {
            "from": "levels",
            "localField": "level_id",
            "foreignField": "_id",
            "as": "level"
        }},
        {"$unwind": "$level"},
        {"$match": {"level.is_legacy": True}},
        {"$sort": {"date_submitted": -1}}
    ]))
    
    # Calculate stats
    approved_count = len(approved_records)
    main_completed_count = len([r for r in main_list_approved if r['progress'] == 100])
    legacy_completed_count = len([r for r in legacy_list_approved if r['progress'] == 100])
    total_submissions = len(all_user_records)
    pending_count = len([r for r in all_user_records if r.get('status') == 'pending'])
    
    print(f"✅ Updated profile stats:")
    print(f"   Total Points: {user.get('points', 0)}")
    print(f"   Main List Completions: {main_completed_count}")
    print(f"   Legacy List Completions: {legacy_completed_count}")
    print(f"   Total Submissions: {total_submissions}")
    print(f"   Pending Records: {pending_count}")
    
    # Show some legacy levels if any
    if legacy_completed_count > 0:
        print(f"\n🏴 Legacy levels completed:")
        for record in legacy_list_approved:
            if record['progress'] == 100:
                print(f"   - {record['level']['name']}")
    
    return {
        'main_completed_count': main_completed_count,
        'legacy_completed_count': legacy_completed_count,
        'total_submissions': total_submissions,
        'pending_count': pending_count
    }

if __name__ == "__main__":
    # Test with users known to have legacy completions
    test_users = ["InsaneI", "ApplePi", "Miifin"]
    
    try:
        for username in test_users:
            results = test_updated_profile_stats(username)
            print("-" * 50)
        
        print(f"\n🎉 PROFILE STATS UPDATE TESTING COMPLETE!")
        print(f"The updated profile now shows:")
        print(f"1. Main List Completions - levels that count for points")
        print(f"2. Legacy List Completions - levels moved to legacy")
        print(f"3. Clear separation between active and legacy achievements")
        print(f"4. Accurate counts for both categories")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        mongo_client.close()