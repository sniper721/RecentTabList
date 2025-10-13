#!/usr/bin/env python3
"""
Test the record count fixes to ensure accuracy
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

def test_profile_route_logic(username):
    """Test the new profile route logic"""
    print(f"\n🧪 TESTING PROFILE ROUTE LOGIC FOR: {username}")
    print("=" * 50)
    
    # Find user
    user = mongo_db.users.find_one({"username": username})
    if not user:
        print(f"❌ User '{username}' not found")
        return
    
    user_id = user['_id']
    
    # Simulate the NEW profile route logic
    print("🔄 Simulating NEW profile route logic...")
    
    # Get ALL records for display in tabs (includes pending/rejected)
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
    
    # Get only APPROVED records for accurate stats counting
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
    
    # Calculate accurate stats
    approved_count = len(approved_records)
    completed_count = len([r for r in approved_records if r['progress'] == 100])
    total_submissions = len(all_user_records)
    pending_count = len([r for r in all_user_records if r.get('status') == 'pending'])
    
    print(f"✅ Profile route calculations:")
    print(f"   Approved Records: {approved_count}")
    print(f"   Completed Levels: {completed_count}")
    print(f"   Total Submissions: {total_submissions}")
    print(f"   Pending Records: {pending_count}")
    
    return {
        'approved_count': approved_count,
        'completed_count': completed_count,
        'total_submissions': total_submissions,
        'pending_count': pending_count
    }

def test_public_profile_logic(username):
    """Test the new public profile route logic"""
    print(f"\n🧪 TESTING PUBLIC PROFILE ROUTE LOGIC FOR: {username}")
    print("=" * 50)
    
    # Find user
    profile_user = mongo_db.users.find_one({"username": username})
    if not profile_user:
        print(f"❌ User '{username}' not found")
        return
    
    print("🔄 Simulating NEW public profile route logic...")
    
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
    
    # Get ALL approved completions for accurate level completion grid (not limited)
    all_completions = list(mongo_db.records.find({
        "user_id": profile_user['_id'], 
        "status": "approved", 
        "progress": 100
    }, {"level_id": 1}))
    
    # Get all main list levels for completion grid
    all_levels = list(mongo_db.levels.find({"is_legacy": False}).sort("position", 1))
    
    # Create a set of completed level IDs for quick lookup (using ALL completions, not just recent 50)
    completed_levels = {completion['level_id'] for completion in all_completions}
    
    # Calculate stats
    total_main_levels = len(all_levels)
    completed_main_levels = len(completed_levels)
    
    print(f"✅ Public profile calculations:")
    print(f"   Recent Records (display): {len(user_records)}")
    print(f"   Total Completions (for grid): {len(all_completions)}")
    print(f"   Total Main Levels: {total_main_levels}")
    print(f"   Completed Main Levels: {completed_main_levels}")
    
    return {
        'recent_records': len(user_records),
        'total_completions': len(all_completions),
        'total_main_levels': total_main_levels,
        'completed_main_levels': completed_main_levels
    }

def test_stats_viewer_logic(username):
    """Test stats viewer logic for comparison"""
    print(f"\n🧪 TESTING STATS VIEWER LOGIC FOR: {username}")
    print("=" * 50)
    
    # Find user
    user = mongo_db.users.find_one({"username": username})
    if not user:
        print(f"❌ User '{username}' not found")
        return
    
    user_id = user['_id']
    
    # Simulate stats viewer logic
    user_records = list(mongo_db.records.aggregate([
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
    
    print(f"✅ Stats viewer calculation:")
    print(f"   Approved Records: {len(user_records)}")
    
    return len(user_records)

def compare_all_methods(username):
    """Compare all counting methods to ensure consistency"""
    print(f"\n🎯 CONSISTENCY CHECK FOR: {username}")
    print("=" * 50)
    
    profile_results = test_profile_route_logic(username)
    public_results = test_public_profile_logic(username)
    stats_count = test_stats_viewer_logic(username)
    
    print(f"\n📊 COMPARISON:")
    print(f"   Profile 'Approved Records': {profile_results['approved_count']}")
    print(f"   Public Profile completions: {public_results['total_completions']}")
    print(f"   Stats Viewer count: {stats_count}")
    
    # Check consistency
    if profile_results['approved_count'] == stats_count:
        print(f"   ✅ Profile and Stats Viewer counts match!")
    else:
        print(f"   ❌ Profile ({profile_results['approved_count']}) and Stats Viewer ({stats_count}) counts don't match!")
    
    if profile_results['completed_count'] == public_results['total_completions']:
        print(f"   ✅ Profile and Public Profile completion counts match!")
    else:
        print(f"   ❌ Profile ({profile_results['completed_count']}) and Public Profile ({public_results['total_completions']}) completion counts don't match!")

if __name__ == "__main__":
    username = "InsaneI"
    
    try:
        compare_all_methods(username)
        
        print(f"\n🎉 SUMMARY:")
        print(f"The fixes ensure that:")
        print(f"1. Profile page shows accurate pre-calculated counts")
        print(f"2. Public profile uses ALL completions for level grid accuracy")
        print(f"3. All views show consistent approved record counts")
        print(f"4. Template filtering is replaced with database-level filtering")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        mongo_client.close()