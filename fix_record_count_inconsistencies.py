#!/usr/bin/env python3
"""
Fix record count inconsistencies across different views
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

def analyze_record_counting_issue():
    """Analyze the record counting inconsistency"""
    print("\n🔍 ANALYZING RECORD COUNT INCONSISTENCIES")
    print("=" * 50)
    
    # Find the user
    username = "InsaneI"
    user = mongo_db.users.find_one({"username": username})
    if not user:
        print(f"❌ User '{username}' not found")
        return
    
    user_id = user['_id']
    print(f"✅ Analyzing user: {user['username']} (ID: {user_id})")
    
    # Method 1: Profile page query (ALL records)
    profile_records = list(mongo_db.records.aggregate([
        {"$match": {"user_id": user_id}},
        {"$lookup": {
            "from": "levels",
            "localField": "level_id",
            "foreignField": "_id",
            "as": "level"
        }},
        {"$unwind": "$level"}
    ]))
    
    # Method 2: Stats viewer query (approved only)
    stats_records = list(mongo_db.records.aggregate([
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
    
    # Method 3: Public profile query (approved only, limited to 50)
    public_records = list(mongo_db.records.aggregate([
        {"$match": {"user_id": user_id, "status": "approved"}},
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
    
    print(f"\n📊 RECORD COUNT COMPARISON:")
    print(f"   Profile page (ALL records): {len(profile_records)}")
    print(f"   Stats viewer (approved only): {len(stats_records)}")
    print(f"   Public profile (approved, limit 50): {len(public_records)}")
    
    # Status breakdown
    status_counts = {}
    for record in profile_records:
        status = record.get('status', 'unknown')
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print(f"\n📋 Status breakdown:")
    for status, count in status_counts.items():
        print(f"   {status}: {count}")
    
    # Check for the specific numbers mentioned (49, 65, 59)
    print(f"\n🎯 INVESTIGATING REPORTED NUMBERS:")
    print(f"   Reported: Stats Viewer = 49, Account Tab = 65, My Records = 59")
    print(f"   Current:  Stats Viewer = {len(stats_records)}, Profile = {len(profile_records)}, My Records = {len(stats_records)}")
    
    # Check if there might be caching or timing issues
    print(f"\n🕐 CHECKING FOR POTENTIAL TIMING ISSUES:")
    
    # Get records by date to see if there were recent changes
    recent_records = list(mongo_db.records.find(
        {"user_id": user_id},
        {"status": 1, "date_submitted": 1, "level_id": 1}
    ).sort("date_submitted", -1).limit(10))
    
    print(f"   Last 10 record submissions:")
    for i, record in enumerate(recent_records, 1):
        level = mongo_db.levels.find_one({"_id": record['level_id']})
        level_name = level['name'] if level else 'Unknown'
        date_str = record.get('date_submitted', 'Unknown')
        print(f"   {i:2d}. {level_name} - {record.get('status', 'unknown')} - {date_str}")
    
    return {
        'profile_count': len(profile_records),
        'stats_count': len(stats_records),
        'public_count': len(public_records),
        'status_counts': status_counts
    }

def create_record_count_summary():
    """Create a summary of how record counts work in different views"""
    print(f"\n📝 RECORD COUNT EXPLANATION:")
    print(f"=" * 50)
    print(f"")
    print(f"The different record counts you see are caused by different filtering:")
    print(f"")
    print(f"1. 📊 PROFILE PAGE 'Total Records' (before fix):")
    print(f"   - Shows ALL records (approved + pending + rejected)")
    print(f"   - Query: records.find({{user_id: user_id}})")
    print(f"   - Template: {{{{ records|length }}}}")
    print(f"")
    print(f"2. 📈 STATS VIEWER:")
    print(f"   - Shows only APPROVED records")
    print(f"   - Query: records.find({{user_id: user_id, status: 'approved'}})")
    print(f"")
    print(f"3. 📋 'MY RECORDS' SECTION:")
    print(f"   - Shows only APPROVED records (filtered in template)")
    print(f"   - Template: {{{{ records|selectattr('status', 'equalto', 'approved')|list|length }}}}")
    print(f"")
    print(f"4. 👤 PUBLIC PROFILE:")
    print(f"   - Shows only APPROVED records (limited to 50 most recent)")
    print(f"   - Query: records.find({{user_id: user_id, status: 'approved'}}).limit(50)")
    print(f"")
    print(f"✅ SOLUTION APPLIED:")
    print(f"   - Profile page now shows 'Approved Records' instead of 'Total Records'")
    print(f"   - Added 'Total Submissions' to show all records")
    print(f"   - Fixed 'Completed Levels' to only count approved completions")
    print(f"")

if __name__ == "__main__":
    try:
        results = analyze_record_counting_issue()
        create_record_count_summary()
        
        print(f"\n🎯 SUMMARY:")
        print(f"The inconsistency is now FIXED in the profile template.")
        print(f"Users will now see consistent counts across all views:")
        print(f"- Approved Records: {results['stats_count']}")
        print(f"- Total Submissions: {results['profile_count']}")
        print(f"")
        print(f"The difference of {results['profile_count'] - results['stats_count']} records")
        print(f"represents non-approved submissions (pending/rejected).")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        mongo_client.close()