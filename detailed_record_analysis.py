#!/usr/bin/env python3
"""
Detailed analysis of record counts and potential caching issues
"""

from pymongo import MongoClient
from bson.objectid import ObjectId
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

# Load environment variables
load_dotenv()

# MongoDB configuration
mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

# Connect to MongoDB
print("Connecting to MongoDB...")
mongo_client = MongoClient(mongodb_uri)
mongo_db = mongo_client[mongodb_db]

def analyze_user_records(username):
    """Detailed analysis of user records"""
    print(f"\n🔍 Detailed analysis for user: {username}")
    
    # Find user
    user = mongo_db.users.find_one({"username": username})
    if not user:
        print(f"❌ User '{username}' not found")
        return
    
    user_id = user['_id']
    print(f"✅ Found user: {user['username']} (ID: {user_id})")
    print(f"   User points: {user.get('points', 0)}")
    
    # Get ALL records with detailed breakdown
    all_records = list(mongo_db.records.find({"user_id": user_id}).sort("date_submitted", -1))
    print(f"\n📊 TOTAL RECORDS: {len(all_records)}")
    
    # Detailed status breakdown
    status_breakdown = {}
    progress_breakdown = {}
    recent_records = []
    
    for record in all_records:
        status = record.get('status', 'unknown')
        progress = record.get('progress', 0)
        
        status_breakdown[status] = status_breakdown.get(status, 0) + 1
        
        if progress == 100:
            progress_breakdown['completed'] = progress_breakdown.get('completed', 0) + 1
        else:
            progress_breakdown['partial'] = progress_breakdown.get('partial', 0) + 1
        
        # Get recent records (last 10)
        if len(recent_records) < 10:
            level = mongo_db.levels.find_one({"_id": record['level_id']})
            recent_records.append({
                'level_name': level['name'] if level else 'Unknown',
                'progress': progress,
                'status': status,
                'date': record.get('date_submitted', 'Unknown')
            })
    
    print(f"\n📋 Status breakdown:")
    for status, count in status_breakdown.items():
        print(f"   {status}: {count}")
    
    print(f"\n🎯 Progress breakdown:")
    for progress_type, count in progress_breakdown.items():
        print(f"   {progress_type}: {count}")
    
    # Simulate different counting methods
    print(f"\n🔢 Different counting methods:")
    
    # Method 1: Profile page (ALL records)
    profile_count = len(all_records)
    print(f"   Profile page method (ALL): {profile_count}")
    
    # Method 2: Stats viewer (approved only)
    approved_records = [r for r in all_records if r.get('status') == 'approved']
    stats_count = len(approved_records)
    print(f"   Stats viewer method (approved): {stats_count}")
    
    # Method 3: My Records section (approved only, displayed)
    my_records_count = len([r for r in all_records if r.get('status') == 'approved'])
    print(f"   'My Records' section: {my_records_count}")
    
    # Method 4: Check if there are any aggregation differences
    # This simulates the profile route aggregation
    aggregated_records = list(mongo_db.records.aggregate([
        {"$match": {"user_id": user_id}},
        {"$lookup": {
            "from": "levels",
            "localField": "level_id",
            "foreignField": "_id",
            "as": "level"
        }},
        {"$unwind": "$level"}
    ]))
    aggregation_count = len(aggregated_records)
    print(f"   Profile aggregation method: {aggregation_count}")
    
    # Method 5: Check approved aggregation (stats viewer method)
    approved_aggregated = list(mongo_db.records.aggregate([
        {"$match": {"user_id": user_id, "status": "approved"}},
        {"$lookup": {
            "from": "levels",
            "localField": "level_id",
            "foreignField": "_id",
            "as": "level"
        }},
        {"$unwind": "$level"}
    ]))
    approved_agg_count = len(approved_aggregated)
    print(f"   Stats viewer aggregation: {approved_agg_count}")
    
    # Check for orphaned records (records without valid levels)
    orphaned_count = 0
    for record in all_records:
        level = mongo_db.levels.find_one({"_id": record['level_id']})
        if not level:
            orphaned_count += 1
    
    if orphaned_count > 0:
        print(f"   ⚠️  Orphaned records (no level): {orphaned_count}")
    
    print(f"\n📅 Recent records (last 10):")
    for i, record in enumerate(recent_records, 1):
        date_str = record['date'].strftime('%Y-%m-%d %H:%M') if isinstance(record['date'], datetime) else str(record['date'])
        print(f"   {i:2d}. {record['level_name']} - {record['progress']}% - {record['status']} - {date_str}")
    
    # Check for potential data integrity issues
    print(f"\n🔍 Data integrity check:")
    if profile_count != aggregation_count:
        print(f"   ❌ Profile count mismatch: direct ({profile_count}) vs aggregation ({aggregation_count})")
    else:
        print(f"   ✅ Profile counts match")
    
    if stats_count != approved_agg_count:
        print(f"   ❌ Stats count mismatch: direct ({stats_count}) vs aggregation ({approved_agg_count})")
    else:
        print(f"   ✅ Stats counts match")
    
    return {
        'profile_count': profile_count,
        'stats_count': stats_count,
        'my_records_count': my_records_count,
        'status_breakdown': status_breakdown,
        'orphaned_count': orphaned_count
    }

if __name__ == "__main__":
    username = "InsaneI"
    
    try:
        results = analyze_user_records(username)
        
        print(f"\n🎯 FINAL ANALYSIS:")
        print(f"The three different counts you're seeing are:")
        print(f"1. Profile 'Total Records': {results['profile_count']} (includes ALL records)")
        print(f"2. Stats Viewer: {results['stats_count']} (approved records only)")
        print(f"3. 'My Records' section: {results['my_records_count']} (approved records only)")
        
        if results['orphaned_count'] > 0:
            print(f"⚠️  Warning: {results['orphaned_count']} orphaned records found")
        
        print(f"\n💡 The discrepancy is caused by including/excluding:")
        for status, count in results['status_breakdown'].items():
            if status != 'approved':
                print(f"   - {count} {status} records")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        mongo_client.close()