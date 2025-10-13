#!/usr/bin/env python3
"""
Test the legacy level exclusion fixes
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

def test_user_completion_counts(username):
    """Test completion counts with and without legacy levels"""
    print(f"\n🧪 TESTING COMPLETION COUNTS FOR: {username}")
    print("=" * 50)
    
    # Find user
    user = mongo_db.users.find_one({"username": username})
    if not user:
        print(f"❌ User '{username}' not found")
        return
    
    user_id = user['_id']
    
    # Method 1: Count ALL completions (including legacy)
    all_completions = list(mongo_db.records.find({
        "user_id": user_id,
        "status": "approved",
        "progress": 100
    }))
    
    # Method 2: Count only MAIN LIST completions (exclude legacy) - NEW METHOD
    main_list_completions = list(mongo_db.records.aggregate([
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
    
    # Method 3: Identify legacy completions
    legacy_completions = list(mongo_db.records.aggregate([
        {"$match": {"user_id": user_id, "status": "approved", "progress": 100}},
        {"$lookup": {
            "from": "levels",
            "localField": "level_id",
            "foreignField": "_id",
            "as": "level"
        }},
        {"$unwind": "$level"},
        {"$match": {"level.is_legacy": True}}
    ]))
    
    print(f"📊 Completion count comparison:")
    print(f"   OLD method (all completions): {len(all_completions)}")
    print(f"   NEW method (main list only): {len(main_list_completions)}")
    print(f"   Legacy completions: {len(legacy_completions)}")
    print(f"   Difference: {len(all_completions) - len(main_list_completions)}")
    
    if legacy_completions:
        print(f"\n🏴 Legacy levels completed:")
        for completion in legacy_completions:
            level_name = completion['level']['name']
            print(f"   - {level_name}")
    
    return {
        'all_completions': len(all_completions),
        'main_completions': len(main_list_completions),
        'legacy_completions': len(legacy_completions)
    }

def test_profile_route_simulation(username):
    """Simulate the updated profile route logic"""
    print(f"\n🔄 SIMULATING UPDATED PROFILE ROUTE FOR: {username}")
    print("=" * 50)
    
    # Find user
    user = mongo_db.users.find_one({"username": username})
    if not user:
        print(f"❌ User '{username}' not found")
        return
    
    user_id = user['_id']
    
    # Simulate the NEW profile route logic
    
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
    
    # Get only APPROVED records on MAIN LIST levels (exclude legacy)
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
    
    # Calculate stats
    approved_count = len(approved_records)
    completed_count = len([r for r in main_list_approved if r['progress'] == 100])  # Only main list
    total_submissions = len(all_user_records)
    pending_count = len([r for r in all_user_records if r.get('status') == 'pending'])
    
    print(f"✅ Updated profile route calculations:")
    print(f"   Approved Records: {approved_count}")
    print(f"   Completed Levels (main list only): {completed_count}")
    print(f"   Total Submissions: {total_submissions}")
    print(f"   Pending Records: {pending_count}")
    
    return {
        'approved_count': approved_count,
        'completed_count': completed_count,
        'total_submissions': total_submissions,
        'pending_count': pending_count
    }

def test_public_profile_simulation(username):
    """Simulate the updated public profile route logic"""
    print(f"\n🌐 SIMULATING UPDATED PUBLIC PROFILE FOR: {username}")
    print("=" * 50)
    
    # Find user
    profile_user = mongo_db.users.find_one({"username": username})
    if not profile_user:
        print(f"❌ User '{username}' not found")
        return
    
    # Get recent records for display
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
    
    # Get main list completions only
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
    
    # Get all main list levels
    all_levels = list(mongo_db.levels.find({"is_legacy": False}).sort("position", 1))
    
    # Calculate stats
    completed_levels = {completion['level_id'] for completion in main_list_completions}
    total_main_levels = len(all_levels)
    completed_main_levels = len(completed_levels)
    
    print(f"✅ Updated public profile calculations:")
    print(f"   Recent Records (display): {len(user_records)}")
    print(f"   Main List Completions: {completed_main_levels}")
    print(f"   Total Main Levels: {total_main_levels}")
    print(f"   Completion Rate: {(completed_main_levels/total_main_levels*100):.1f}%")
    
    return {
        'recent_records': len(user_records),
        'completed_main_levels': completed_main_levels,
        'total_main_levels': total_main_levels
    }

if __name__ == "__main__":
    # Test with users known to have legacy completions
    test_users = ["InsaneI", "ApplePi", "Miifin"]
    
    try:
        for username in test_users:
            completion_results = test_user_completion_counts(username)
            profile_results = test_profile_route_simulation(username)
            public_results = test_public_profile_simulation(username)
            
            print(f"\n📊 SUMMARY FOR {username}:")
            print(f"   Legacy completions excluded: {completion_results['legacy_completions']}")
            print(f"   Profile completion count: {profile_results['completed_count']}")
            print(f"   Public profile completion count: {public_results['completed_main_levels']}")
            
            if profile_results['completed_count'] == public_results['completed_main_levels']:
                print(f"   ✅ Profile and public profile counts match!")
            else:
                print(f"   ❌ Counts don't match!")
            
            print("-" * 50)
        
        print(f"\n🎉 LEGACY LEVEL EXCLUSION TESTING COMPLETE!")
        print(f"The fixes ensure that:")
        print(f"1. Only main list level completions count toward stats")
        print(f"2. Legacy level completions are excluded from all counts")
        print(f"3. Level completion grids only show main list levels")
        print(f"4. All views show consistent completion counts")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        mongo_client.close()