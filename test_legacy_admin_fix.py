#!/usr/bin/env python3
"""
Test script to verify the legacy list admin panel fix
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
    print("🔍 Testing legacy list admin panel fix...")
    
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
    
    # Test legacy levels query (same as admin panel)
    print("\n🔍 Testing legacy levels query...")
    legacy_levels = list(mongo_db.levels.find({"is_legacy": True}, {
        "name": 1, "creator": 1, "verifier": 1, "position": 1, "points": 1, 
        "level_id": 1, "difficulty": 1, "is_legacy": 1, "level_type": 1,
        "demon_type": 1, "min_percentage": 1
    }).sort("position", 1))
    
    print(f"📊 Found {len(legacy_levels)} legacy levels")
    
    if legacy_levels:
        print(f"\n🏆 First 10 legacy levels:")
        for i, level in enumerate(legacy_levels[:10]):
            pos = level.get("position", "?")
            name = level.get("name", "Unknown")
            creator = level.get("creator", "Unknown")
            points = level.get("points", 0)
            print(f"  #{pos}: {name} by {creator} ({points} points)")
        
        if len(legacy_levels) > 10:
            print(f"  ... and {len(legacy_levels) - 10} more")
        
        # Check position range
        positions = [level.get("position", 0) for level in legacy_levels]
        min_pos = min(positions) if positions else 0
        max_pos = max(positions) if positions else 0
        
        print(f"\n📊 Legacy position range: {min_pos} - {max_pos}")
        
        if min_pos >= 151:
            print("✅ Legacy levels start at position 151 or higher (correct)")
        else:
            print(f"⚠️  Some legacy levels have positions below 151")
        
        print("✅ Legacy list should now be visible in admin panel")
    else:
        print("⚠️  No legacy levels found - this might be why admin panel shows empty list")
        
        # Check if there are any levels marked as legacy
        any_legacy = mongo_db.levels.count_documents({"is_legacy": True})
        print(f"📊 Total levels with is_legacy=True: {any_legacy}")
        
        if any_legacy == 0:
            print("❌ No levels are marked as legacy - this explains the empty admin panel")
        
    # Test main list count
    main_count = mongo_db.levels.count_documents({"is_legacy": {"$ne": True}})
    print(f"\n📊 Main list levels: {main_count}")
    
    if main_count == 150:
        print("✅ Main list has exactly 150 levels (correct)")
    else:
        print(f"⚠️  Main list should have 150 levels, but has {main_count}")

if __name__ == "__main__":
    main()