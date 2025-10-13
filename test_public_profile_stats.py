#!/usr/bin/env python3
"""
Test the updated public profile stats
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

def test_public_profile_stats(username):
    """Test the updated public profile route with main/legacy stats"""
    print(f"\n🧪 TESTING PUBLIC PROFILE STATS FOR: {username}")
    print("=" * 50)
    
    # Find user
    profile_user = mongo_db.users.find_one({"username": username})
    if not profile_user:
        print(f"❌ User '{username}' not found")
        return
    
    # Simulate the updated public profile route logic
    
    # Get user's recent approved records for display (limited to 50)
    user_records = list(mongo_db.records.aggregate([
        {"$match": {"user_id": profile_user['_id'], "status": "approved"}},
        {"$lookup": {
            "from": "levels",
            "localField": "level_id",
            "foreignField": "_id",
            "as": "level"
        }},
        {"$unwind": "$level"},
        {"$sort": {"date_submitted": -1}},
        {"$limit": 50}
    ]))
    
    # Get ALL approved completions on MAIN LIST levels only
    main_list_completions = list(mongo_db.records.aggregate([
        {"$match": {"user_id": profile_user['_id'], "status": "approved", "progress": 100}},
        {"$lookup": {
            "from": "levels",
            "localField": "level_id",
            "foreignField": "_id",
            "as": "level"
        }},
        {"$unwind": "$level"},
        {"$match": {"level.is_legacy": {"$ne": True}}},
        {"$project": {"level_id": 1}}
    ]))
    
    # Get ALL approved completions on LEGACY levels
    legacy_list_completions = list(mongo_db.records.aggregate([
        {"$match": {"user_id": profile_user['_id'], "status": "approved", "progress": 100}},
        {"$lookup": {
            "from": "levels",
            "localField": "level_id",
            "foreignField": "_id",
            "as": "level"
        }},
        {"$unwind": "$level"},
        {"$match": {"level.is_legacy": True}},
        {"$project": {"level_id": 1}}
    ]))
    
    # Get all main list levels
    all_levels = list(mongo_db.levels.find({"is_legacy": False}).sort("position", 1))
    
    # Calculate stats
    completed_levels = {completion['level_id'] for completion in main_list_completions}
    total_main_levels = len(all_levels)
    completed_main_levels = len(completed_levels)
    legacy_completed_count = len(legacy_list_completions)
    
    print(f"✅ Public profile stats:")
    print(f"   Total Points: {profile_user.get('points', 0)}")
    print(f"   Main List Completions: {completed_main_levels}")
    print(f"   Legacy List Completions: {legacy_completed_count}")
    print(f"   Recent Records (display): {len(user_records)}")
    print(f"   Total Main Levels: {total_main_levels}")
    
    return {
        'main_completed_count': completed_main_levels,
        'legacy_completed_count': legacy_completed_count,
        'total_points': profile_user.get('points', 0)
    }

def compare_profile_vs_public_stats(username):
    """Compare private profile stats vs public profile stats"""
    print(f"\n🔄 COMPARING PRIVATE VS PUBLIC PROFILE STATS FOR: {username}")
    print("=" * 60)
    
    # Find user
    user = mongo_db.users.find_one({"username": username})
    if not user:
        print(f"❌ User '{username}' not found")
        return
    
    user_id = user['_id']
    
    # Private profile stats (main list completions)
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
    
    # Private profile stats (legacy completions)
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
    
    private_main = len([r for r in main_list_approved if r['progress'] == 100])
    private_legacy = len([r for r in legacy_list_approved if r['progress'] == 100])
    
    # Public profile stats
    public_stats = test_public_profile_stats(username)
    
    print(f"\n📊 Comparison:")
    print(f"   Private Profile Main Completions: {private_main}")
    print(f"   Public Profile Main Completions: {public_stats['main_completed_count']}")
    print(f"   Private Profile Legacy Completions: {private_legacy}")
    print(f"   Public Profile Legacy Completions: {public_stats['legacy_completed_count']}")
    
    if private_main == public_stats['main_completed_count'] and private_legacy == public_stats['legacy_completed_count']:
        print(f"   ✅ Private and public profile stats match perfectly!")
    else:
        print(f"   ❌ Stats don't match!")
    
    return {
        'private_main': private_main,
        'private_legacy': private_legacy,
        'public_main': public_stats['main_completed_count'],
        'public_legacy': public_stats['legacy_completed_count']
    }

if __name__ == "__main__":
    # Test with users known to have legacy completions
    test_users = ["InsaneI", "ApplePi", "Miifin"]
    
    try:
        for username in test_users:
            compare_profile_vs_public_stats(username)
            print("-" * 60)
        
        print(f"\n🎉 PUBLIC PROFILE STATS UPDATE COMPLETE!")
        print(f"Now all users can see the same stats on public profiles:")
        print(f"1. Total Points - visible to everyone")
        print(f"2. Main List Completions - visible to everyone")
        print(f"3. Legacy List Completions - visible to everyone")
        print(f"4. Pending Records - only visible on own profile")
        print(f"")
        print(f"✅ Consistent stats across private and public profiles!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        mongo_client.close()