#!/usr/bin/env python3
"""
Detailed analysis of InsaneI's record for the level "cry"
"""

import os
from pymongo import MongoClient
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB configuration
mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

def main():
    try:
        # Connect to MongoDB
        print("Connecting to MongoDB...")
        client = MongoClient(mongodb_uri)
        db = client[mongodb_db]
        
        # Test connection
        client.admin.command('ping')
        print("✅ Connected to MongoDB successfully")
        
        # Find InsaneI and cry level
        user = db.users.find_one({"username": {"$regex": "^insaneI$", "$options": "i"}})
        cry_level = db.levels.find_one({"name": {"$regex": "^cry$", "$options": "i"}})
        
        print(f"\n👤 User: {user['username']} (ID: {user['_id']})")
        print(f"🎮 Level: {cry_level['name']} (ID: {cry_level['_id']}, Position: {cry_level.get('position', 'N/A')})")
        
        # Get ALL records for cry level (from all users) to see the history
        print(f"\n📋 ALL records for 'cry' level:")
        all_cry_records = list(db.records.find({"level_id": cry_level['_id']}).sort("date_submitted", 1))
        
        print(f"Total records for 'cry': {len(all_cry_records)}")
        
        for i, record in enumerate(all_cry_records, 1):
            user_record = db.users.find_one({"_id": record['user_id']})
            username = user_record['username'] if user_record else f"User ID: {record['user_id']}"
            status = record.get('status', 'unknown')
            progress = record.get('progress', 0)
            date_submitted = record.get('date_submitted', 'unknown')
            video_url = record.get('video_url', 'No video')
            
            print(f"  {i}. {username}: {status}, {progress}%, {date_submitted}")
            if video_url != 'No video':
                print(f"     Video: {video_url}")
        
        # Check specifically for InsaneI's record
        print(f"\n🎯 InsaneI's record for 'cry':")
        insanei_cry_record = db.records.find_one({
            "user_id": user['_id'],
            "level_id": cry_level['_id']
        })
        
        if insanei_cry_record:
            print("✅ Record found!")
            print(f"   Status: {insanei_cry_record.get('status', 'unknown')}")
            print(f"   Progress: {insanei_cry_record.get('progress', 0)}%")
            print(f"   Date submitted: {insanei_cry_record.get('date_submitted', 'unknown')}")
            print(f"   Video URL: {insanei_cry_record.get('video_url', 'No video')}")
            print(f"   Record ID: {insanei_cry_record['_id']}")
            
            # Check if this record is in admin logs
            print(f"\n🔍 Admin actions on this specific record:")
            admin_actions = list(db.admin_logs.find({
                "$or": [
                    {"details": {"$regex": str(insanei_cry_record['_id'])}},
                    {"details": {"$regex": "cry.*InsaneI", "$options": "i"}},
                    {"details": {"$regex": "InsaneI.*cry", "$options": "i"}}
                ]
            }).sort("timestamp", -1))
            
            if admin_actions:
                for action in admin_actions:
                    timestamp = action.get('timestamp', 'unknown')
                    action_type = action.get('action', 'unknown')
                    admin_user = action.get('admin_username', 'unknown')
                    details = action.get('details', '')
                    print(f"   - {timestamp}: {action_type} by {admin_user}")
                    print(f"     Details: {details}")
            else:
                print("   No specific admin actions found for this record")
                
        else:
            print("❌ No record found for InsaneI on 'cry' level!")
            print("This suggests the record may have been deleted or never existed.")
        
        # Check for any deleted records (if there's a deleted_records collection)
        print(f"\n🗑️ Checking for deleted records...")
        try:
            deleted_records = list(db.deleted_records.find({
                "user_id": user['_id'],
                "level_id": cry_level['_id']
            }))
            
            if deleted_records:
                print(f"Found {len(deleted_records)} deleted records:")
                for record in deleted_records:
                    print(f"   - Deleted on: {record.get('deleted_at', 'unknown')}")
                    print(f"     Original status: {record.get('status', 'unknown')}")
                    print(f"     Progress: {record.get('progress', 0)}%")
                    print(f"     Deleted by: {record.get('deleted_by', 'unknown')}")
            else:
                print("No deleted records found")
                
        except Exception as e:
            print(f"No deleted_records collection or error: {e}")
        
        # Check recent admin activity around cry level
        print(f"\n📅 Recent admin activity involving 'cry' level:")
        cry_admin_logs = list(db.admin_logs.find({
            "details": {"$regex": "cry", "$options": "i"}
        }).sort("timestamp", -1).limit(10))
        
        if cry_admin_logs:
            for log in cry_admin_logs:
                timestamp = log.get('timestamp', 'unknown')
                action = log.get('action', 'unknown')
                admin_user = log.get('admin_username', 'unknown')
                details = log.get('details', '')
                print(f"   - {timestamp}: {action} by {admin_user}")
                print(f"     {details}")
        else:
            print("No recent admin activity found for 'cry' level")
            
        print(f"\n✅ Detailed analysis complete")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()