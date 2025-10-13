#!/usr/bin/env python3
"""
Check insaneI's records to see if they lost any records, particularly for the level "cry"
"""

import os
from pymongo import MongoClient
from datetime import datetime, timezone, timedelta
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
        
        # Find insaneI user
        print("\n🔍 Looking for insaneI user...")
        user = db.users.find_one({"username": {"$regex": "^insaneI$", "$options": "i"}})
        
        if not user:
            print("❌ User 'insaneI' not found")
            # Try variations
            print("Searching for similar usernames...")
            similar_users = list(db.users.find({"username": {"$regex": "insane", "$options": "i"}}))
            for u in similar_users:
                print(f"  - {u['username']} (ID: {u['_id']})")
            return
        
        print(f"✅ Found user: {user['username']} (ID: {user['_id']})")
        user_id = user['_id']
        
        # Find the "cry" level
        print("\n🔍 Looking for level 'cry'...")
        cry_level = db.levels.find_one({"name": {"$regex": "^cry$", "$options": "i"}})
        
        if not cry_level:
            print("❌ Level 'cry' not found")
            # Try variations
            print("Searching for similar level names...")
            similar_levels = list(db.levels.find({"name": {"$regex": "cry", "$options": "i"}}))
            for level in similar_levels:
                print(f"  - {level['name']} (ID: {level['_id']}, Position: {level.get('position', 'N/A')})")
        else:
            print(f"✅ Found level: {cry_level['name']} (ID: {cry_level['_id']}, Position: {cry_level.get('position', 'N/A')})")
        
        # Get all records for insaneI
        print(f"\n📋 Getting all records for {user['username']}...")
        all_records = list(db.records.find({"user_id": user_id}).sort("date_submitted", -1))
        
        print(f"Total records found: {len(all_records)}")
        
        # Categorize records
        approved_records = [r for r in all_records if r.get('status') == 'approved']
        pending_records = [r for r in all_records if r.get('status') == 'pending']
        rejected_records = [r for r in all_records if r.get('status') == 'rejected']
        
        print(f"  - Approved: {len(approved_records)}")
        print(f"  - Pending: {len(pending_records)}")
        print(f"  - Rejected: {len(rejected_records)}")
        
        # Check for cry level specifically
        if cry_level:
            cry_records = [r for r in all_records if r.get('level_id') == cry_level['_id']]
            print(f"\n🎯 Records for 'cry' level: {len(cry_records)}")
            
            for record in cry_records:
                status = record.get('status', 'unknown')
                progress = record.get('progress', 0)
                date_submitted = record.get('date_submitted', 'unknown')
                print(f"  - Status: {status}, Progress: {progress}%, Date: {date_submitted}")
        
        # Show recent records (last 30 days)
        print(f"\n📅 Recent records (last 30 days):")
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        
        recent_records = []
        for r in all_records:
            if r.get('date_submitted'):
                date_submitted = r['date_submitted']
                # Handle timezone-naive dates
                if date_submitted.tzinfo is None:
                    date_submitted = date_submitted.replace(tzinfo=timezone.utc)
                if date_submitted > thirty_days_ago:
                    recent_records.append(r)
        print(f"Found {len(recent_records)} recent records")
        
        for record in recent_records[:10]:  # Show first 10
            level = db.levels.find_one({"_id": record.get('level_id')})
            level_name = level['name'] if level else f"Level ID: {record.get('level_id')}"
            status = record.get('status', 'unknown')
            progress = record.get('progress', 0)
            date_submitted = record.get('date_submitted', 'unknown')
            print(f"  - {level_name}: {status}, {progress}%, {date_submitted}")
        
        # Check for any deleted/modified records in logs (if available)
        print(f"\n🔍 Checking for admin actions on insaneI's records...")
        try:
            admin_logs = list(db.admin_logs.find({
                "$or": [
                    {"details": {"$regex": str(user_id)}},
                    {"details": {"$regex": user['username'], "$options": "i"}}
                ]
            }).sort("timestamp", -1).limit(20))
            
            print(f"Found {len(admin_logs)} admin log entries")
            for log in admin_logs:
                action = log.get('action', 'unknown')
                timestamp = log.get('timestamp', 'unknown')
                details = log.get('details', '')
                admin_user = log.get('admin_username', 'unknown')
                print(f"  - {timestamp}: {action} by {admin_user} - {details}")
                
        except Exception as e:
            print(f"No admin logs found or error accessing them: {e}")
        
        # Check security logs for any suspicious activity
        print(f"\n🔒 Checking security logs...")
        try:
            security_logs = list(db.security_logs.find({
                "$or": [
                    {"user_id": user_id},
                    {"details": {"$regex": user['username'], "$options": "i"}}
                ]
            }).sort("timestamp", -1).limit(10))
            
            print(f"Found {len(security_logs)} security log entries")
            for log in security_logs:
                event_type = log.get('event_type', 'unknown')
                timestamp = log.get('timestamp', 'unknown')
                ip_address = log.get('ip_address', 'unknown')
                print(f"  - {timestamp}: {event_type} from {ip_address}")
                
        except Exception as e:
            print(f"No security logs found or error accessing them: {e}")
            
        print(f"\n✅ Analysis complete for {user['username']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()