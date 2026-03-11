"""
Test script to verify the index route loads all levels correctly
"""
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import time

# Load environment variables
load_dotenv()

# Get MongoDB configuration
mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

print("=" * 80)
print("Testing Index Route Level Loading")
print("=" * 80)

# Connect to MongoDB
mongo_client = MongoClient(
    mongodb_uri,
    tls=True,
    tlsAllowInvalidCertificates=True,
    tlsAllowInvalidHostnames=True,
    serverSelectionTimeoutMS=30000,
    socketTimeoutMS=45000,
    connectTimeoutMS=30000,
    maxPoolSize=10,
    minPoolSize=2,
    directConnection=False,
    connect=False
)

db = mongo_client[mongodb_db]

# Test the new query (without projection and limit)
print("\n📊 Testing NEW query (no projection, no limit)...")
start_time = time.time()
try:
    main_list = list(db.levels.find(
        {"is_legacy": {"$ne": True}}
    ).sort("position", 1))
    
    load_time = (time.time() - start_time) * 1000
    print(f"✅ SUCCESS!")
    print(f"   Loaded {len(main_list)} levels in {load_time:.2f}ms")
    
    if len(main_list) > 0:
        print(f"\n   First 5 levels:")
        for level in main_list[:5]:
            print(f"      #{level.get('position')} - {level.get('name')} ({level.get('points')} pts)")
    
    if len(main_list) < 150:
        print(f"\n⚠️  WARNING: Only {len(main_list)} levels found. Expected 150+ levels!")
        
except Exception as e:
    print(f"❌ FAILED: {e}")

# Test the OLD query (with projection and limit)
print("\n\n📊 Testing OLD query (with projection and limit of 200)...")
start_time = time.time()
try:
    old_list = list(db.levels.find(
        {"is_legacy": False},
        {"_id": 1, "name": 1, "creator": 1, "verifier": 1, "position": 1, "points": 1, "level_id": 1, "difficulty": 1, "thumbnail_url": 1, "video_url": 1, "min_percentage": 1}
    ).sort("position", 1).limit(200))
    
    load_time = (time.time() - start_time) * 1000
    print(f"✅ SUCCESS!")
    print(f"   Loaded {len(old_list)} levels in {load_time:.2f}ms")
    
except Exception as e:
    print(f"❌ FAILED: {e}")

# Check for cache issues
print("\n\n📊 Checking for potential cache issues...")
settings = db.site_settings.find_one({"_id": "cache"})
if settings:
    print(f"Cache settings found: {settings}")
else:
    print("No cache settings found in database")

# Count total levels again
total = db.levels.count_documents({"is_legacy": {"$ne": True}})
print(f"\n📊 Total main list levels in database: {total}")

print("\n" + "=" * 80)
print("Test complete!")
print("=" * 80)
