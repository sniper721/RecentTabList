#!/usr/bin/env python3
"""
Verify the changes made to legacy list and points system
"""
import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB configuration
mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

def main():
    print("🔍 Verifying legacy list reversal and points recalculation...")
    
    # Connect to MongoDB
    try:
        mongo_client = MongoClient(
            mongodb_uri,
            tls=True,
            tlsAllowInvalidCertificates=True,
            tlsAllowInvalidHostnames=True,
            serverSelectionTimeoutMS=30000
        )
        mongo_db = mongo_client[mongodb_db]
        mongo_client.admin.command('ping')
        print("✅ Connected to MongoDB successfully")
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        return
    
    # Check legacy list
    legacy = list(mongo_db.levels.find({'is_legacy': True}).sort('position', 1))
    print(f"\n📊 Legacy List Status:")
    print(f"Total legacy levels: {len(legacy)}")
    print(f"Position range: #{legacy[0]['position']} to #{legacy[-1]['position']}")
    print(f"First level: {legacy[0]['name']} at #{legacy[0]['position']}")
    print(f"Last level: {legacy[-1]['name']} at #{legacy[-1]['position']}")
    
    # Check points for key positions
    print(f"\n📊 Points Verification:")
    test_positions = [1, 50, 100, 101, 150, 209]
    for pos in test_positions:
        level = mongo_db.levels.find_one({'position': pos})
        if level:
            points = level.get('points', 0)
            status = "Legacy" if level.get('is_legacy') else "Main"
            print(f"  #{pos} ({status}): {points} points")
    
    # Check user points
    print(f"\n📊 Top Users Points:")
    top_users = list(mongo_db.users.find().sort('points', -1).limit(5))
    for user in top_users:
        print(f"  {user.get('username', 'Unknown')}: {user.get('points', 0)} points")

if __name__ == "__main__":
    main()