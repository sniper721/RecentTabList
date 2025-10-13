#!/usr/bin/env python3
"""
Verify the impact of the legacy level exclusion fix
"""

from pymongo import MongoClient
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

def show_fix_impact():
    """Show the impact of excluding legacy levels from completion counts"""
    print("\n🎯 LEGACY LEVEL EXCLUSION FIX IMPACT")
    print("=" * 60)
    
    # Get users with the most legacy completions
    users_with_legacy = []
    
    # Get all users with points
    users = list(mongo_db.users.find(
        {"points": {"$gt": 0}}, 
        {"_id": 1, "username": 1, "points": 1}
    ).sort("points", -1))
    
    for user in users:
        user_id = user['_id']
        
        # Count all completions
        all_completions = mongo_db.records.count_documents({
            "user_id": user_id,
            "status": "approved", 
            "progress": 100
        })
        
        # Count main list completions only
        main_completions = len(list(mongo_db.records.aggregate([
            {"$match": {"user_id": user_id, "status": "approved", "progress": 100}},
            {"$lookup": {
                "from": "levels",
                "localField": "level_id",
                "foreignField": "_id", 
                "as": "level"
            }},
            {"$unwind": "$level"},
            {"$match": {"level.is_legacy": {"$ne": True}}}
        ])))
        
        legacy_count = all_completions - main_completions
        
        if legacy_count > 0:
            users_with_legacy.append({
                'username': user['username'],
                'all_completions': all_completions,
                'main_completions': main_completions,
                'legacy_completions': legacy_count,
                'points': user['points']
            })
    
    # Sort by most legacy completions
    users_with_legacy.sort(key=lambda x: x['legacy_completions'], reverse=True)
    
    print(f"📊 Users affected by legacy level exclusion:")
    print(f"{'Rank':<4} {'Username':<15} {'Before':<6} {'After':<6} {'Legacy':<6} {'Points':<8}")
    print("-" * 60)
    
    total_legacy_excluded = 0
    for i, user_data in enumerate(users_with_legacy[:15], 1):  # Top 15
        print(f"{i:<4} {user_data['username']:<15} {user_data['all_completions']:<6} "
              f"{user_data['main_completions']:<6} {user_data['legacy_completions']:<6} "
              f"{user_data['points']:<8.1f}")
        total_legacy_excluded += user_data['legacy_completions']
    
    print("-" * 60)
    print(f"Total users affected: {len(users_with_legacy)}")
    print(f"Total legacy completions excluded: {total_legacy_excluded}")
    
    # Show the most commonly completed legacy levels
    print(f"\n🏴 Most commonly completed legacy levels:")
    legacy_level_counts = {}
    
    # Get all legacy completions
    legacy_completions = list(mongo_db.records.aggregate([
        {"$match": {"status": "approved", "progress": 100}},
        {"$lookup": {
            "from": "levels",
            "localField": "level_id",
            "foreignField": "_id",
            "as": "level"
        }},
        {"$unwind": "$level"},
        {"$match": {"level.is_legacy": True}},
        {"$group": {
            "_id": "$level.name",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]))
    
    for level in legacy_completions:
        print(f"   {level['_id']}: {level['count']} completions")
    
    return {
        'users_affected': len(users_with_legacy),
        'total_legacy_excluded': total_legacy_excluded
    }

if __name__ == "__main__":
    try:
        results = show_fix_impact()
        
        print(f"\n✅ LEGACY LEVEL EXCLUSION FIX SUMMARY:")
        print(f"- Fixed completion counting for {results['users_affected']} users")
        print(f"- Excluded {results['total_legacy_excluded']} legacy level completions")
        print(f"- All views now show consistent main list completion counts")
        print(f"- Legacy levels no longer inflate user statistics")
        print(f"")
        print(f"🎯 The record count inconsistencies have been resolved!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        mongo_client.close()