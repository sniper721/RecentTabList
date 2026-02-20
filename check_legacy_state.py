#!/usr/bin/env python3
"""
Check current legacy list state
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
    print("🔍 Checking current legacy list state...")
    
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
    
    # Get legacy levels
    legacy = list(mongo_db.levels.find({'is_legacy': True}).sort('position', 1))
    
    print(f"\n📊 Current Legacy List Status:")
    print(f"Total legacy levels: {len(legacy)}")
    
    if legacy:
        print(f"\nFirst 10 legacy levels:")
        for level in legacy[:10]:
            print(f"  #{level['position']}: {level['name']}")
        
        print(f"\nLast 10 legacy levels:")
        for level in legacy[-10:]:
            print(f"  #{level['position']}: {level['name']}")
        
        print(f"\nPosition range: {legacy[0]['position']} to {legacy[-1]['position']}")
    
    # Get main list
    main_list = list(mongo_db.levels.find({'is_legacy': {'$ne': True}}).sort('position', 1))
    print(f"\n📊 Main List Status:")
    print(f"Total main list levels: {len(main_list)}")
    if main_list:
        print(f"Position range: {main_list[0]['position']} to {main_list[-1]['position']}")

if __name__ == "__main__":
    main()