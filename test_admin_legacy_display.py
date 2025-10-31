#!/usr/bin/env python3
"""
Test the admin legacy levels display
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
    print("🧪 Testing admin legacy levels display...")
    
    # Connect to MongoDB
    try:
        mongo_client = MongoClient(
            mongodb_uri,
            tls=True,
            tlsAllowInvalidCertificates=False,
            tlsAllowInvalidHostnames=False,
            serverSelectionTimeoutMS=60000,
            socketTimeoutMS=60000,
            connectTimeoutMS=30000
        )
        mongo_db = mongo_client[mongodb_db]
        mongo_client.admin.command('ping')
        print("✅ Connected to MongoDB successfully")
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        return
    
    # Test the exact query used by admin panel for legacy levels
    print("\n🔍 Testing legacy levels query (same as admin panel)...")
    
    legacy_levels = list(mongo_db.levels.find({"is_legacy": True}, {
        "name": 1, "creator": 1, "verifier": 1, "position": 1, "points": 1, 
        "level_id": 1, "difficulty": 1, "is_legacy": 1, "level_type": 1,
        "demon_type": 1, "min_percentage": 1
    }).sort("position", 1))
    
    print(f"📊 Found {len(legacy_levels)} legacy levels")
    
    if legacy_levels:
        print(f"\n✅ Legacy levels found! First 10:")
        for i, level in enumerate(legacy_levels[:10]):
            pos = level.get("position", "?")
            name = level.get("name", "Unknown")
            creator = level.get("creator", "Unknown")
            is_legacy = level.get("is_legacy", False)
            print(f"  #{pos}: {name} by {creator} (is_legacy: {is_legacy})")
        
        if len(legacy_levels) > 10:
            print(f"  ... and {len(legacy_levels) - 10} more")
        
        print(f"\n✅ Admin panel should display these {len(legacy_levels)} legacy levels")
        
        # Check if any have missing fields that might cause display issues
        missing_fields = 0
        for level in legacy_levels:
            required_fields = ['name', 'creator', 'verifier', 'position', 'difficulty']
            for field in required_fields:
                if not level.get(field):
                    missing_fields += 1
                    print(f"⚠️  Level {level.get('name', 'Unknown')} missing field: {field}")
        
        if missing_fields == 0:
            print("✅ All legacy levels have required fields")
        else:
            print(f"⚠️  {missing_fields} field(s) missing across legacy levels")
            
    else:
        print("❌ No legacy levels found!")
        print("This explains why admin panel shows 'No levels in the legacy list'")
        
        # Double-check with a broader query
        any_legacy = mongo_db.levels.count_documents({"is_legacy": True})
        print(f"📊 Double-check: {any_legacy} levels have is_legacy=True")
        
        if any_legacy == 0:
            print("❌ No levels are marked as legacy in the database")
        else:
            print("⚠️  Levels exist but query didn't return them - possible field issue")
    
    # Test main list query for comparison
    print(f"\n🔍 Testing main list query for comparison...")
    main_levels = list(mongo_db.levels.find({"is_legacy": {"$ne": True}}, {
        "name": 1, "creator": 1, "verifier": 1, "position": 1, "points": 1, 
        "level_id": 1, "difficulty": 1, "is_legacy": 1, "level_type": 1,
        "demon_type": 1, "min_percentage": 1
    }).sort("position", 1))
    
    print(f"📊 Found {len(main_levels)} main list levels")
    
    if main_levels:
        print(f"✅ Main list working correctly")
    else:
        print(f"❌ Main list also empty - database issue")

if __name__ == "__main__":
    main()