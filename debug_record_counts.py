#!/usr/bin/env python3
"""
Debug script to identify record count discrepancies
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

def debug_user_records(username):
    """Debug record counts for a specific user"""
    print(f"\n🔍 Debugging record counts for user: {username}")
    
    # Find user
    user = mongo_db.users.find_one({"username": username})
    if not user:
        print(f"❌ User '{username}' not found")
        return
    
    user_id = user['_id']
    print(f"✅ Found user: {user['username']} (ID: {user_id})")
    
    # Get ALL records (like profile page does)
    all_records = list(mongo_db.records.find({"user_id": user_id}))
    print(f"\n📊 ALL RECORDS (Profile page method): {len(all_records)}")
    
    # Get only approved records (like stats viewer does)
    approved_records = list(mongo_db.records.find({"user_id": user_id, "status": "approved"}))
    print(f"✅ APPROVED RECORDS (Stats viewer method): {len(approved_records)}")
    
    # Count by status
    status_counts = {}
    for record in all_records:
        status = record.get('status', 'unknown')
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print(f"\n📋 Records by status:")
    for status, count in status_counts.items():
        print(f"   {status}: {count}")
    
    # Show the actual records in "My Records" section (approved only)
    my_records_count = len([r for r in all_records if r.get('status') == 'approved'])
    print(f"\n📝 'My Records' section count: {my_records_count}")
    
    # Check for any data inconsistencies
    print(f"\n🔍 Data consistency check:")
    print(f"   Profile 'Total Records': {len(all_records)}")
    print(f"   Stats Viewer count: {len(approved_records)}")
    print(f"   'My Records' visible count: {my_records_count}")
    
    if len(approved_records) != my_records_count:
        print(f"❌ INCONSISTENCY: Approved records ({len(approved_records)}) != My Records count ({my_records_count})")
    else:
        print(f"✅ Approved records and My Records count match")
    
    # Show some sample records for debugging
    print(f"\n📄 Sample records (first 5):")
    for i, record in enumerate(all_records[:5]):
        level = mongo_db.levels.find_one({"_id": record['level_id']})
        level_name = level['name'] if level else 'Unknown Level'
        print(f"   {i+1}. {level_name} - {record['progress']}% - Status: {record.get('status', 'unknown')}")
    
    return {
        'all_records': len(all_records),
        'approved_records': len(approved_records),
        'my_records_count': my_records_count,
        'status_counts': status_counts
    }

if __name__ == "__main__":
    # Debug for the user who reported the issue
    # You can change this username to match the actual user
    username = "InsaneI"  # Change this to the actual username
    
    try:
        results = debug_user_records(username)
        
        print(f"\n🎯 SUMMARY:")
        print(f"The discrepancy is likely caused by:")
        print(f"1. Profile page shows ALL records ({results['all_records']}) - includes pending/rejected")
        print(f"2. Stats Viewer shows only APPROVED records ({results['approved_records']})")
        print(f"3. 'My Records' section shows only approved records ({results['my_records_count']})")
        
        if results['all_records'] != results['approved_records']:
            non_approved = results['all_records'] - results['approved_records']
            print(f"\n💡 You have {non_approved} non-approved records (pending/rejected)")
            print(f"   This explains the difference between the counts!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        mongo_client.close()