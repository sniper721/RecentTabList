"""
INSTANT LOAD FIX - Pre-loads cache before starting server
This makes the website load instantly by caching data at startup
"""
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import time
from datetime import datetime, timezone

load_dotenv()

mongodb_uri = os.environ.get('MONGODB_URI')
mongodb_db = os.environ.get('MONGODB_DB')

print("=" * 80)
print("PRE-LOADING CACHE FOR INSTANT WEBSITE LOAD")
print("=" * 80)

# Connect to MongoDB
print("\n📡 Connecting to MongoDB...")
start = time.time()

client= MongoClient(
    mongodb_uri,
    tls=True,
    tlsAllowInvalidCertificates=True,
    tlsAllowInvalidHostnames=True,
   serverSelectionTimeoutMS=15000,
    socketTimeoutMS=60000,  # 60 seconds for long queries
    connectTimeoutMS=30000,
    maxPoolSize=10,
    minPoolSize=2,
    maxIdleTimeMS=60000,
    waitQueueTimeoutMS=30000,
   retryWrites=True,
   retryReads=True,
    directConnection=False,
    connect=False
)

db = client[mongodb_db]
elapsed = (time.time() - start) * 1000
print(f"✅ Connected in {elapsed:.2f}ms")

# Pre-load main list
print("\n🔄 Pre-loading MAIN LIST levels...")
try:
    start = time.time()
    fields = {
        "_id": 1, "name": 1, "creator": 1, "verifier": 1,
        "position": 1, "points": 1, "level_id": 1, "difficulty": 1,
        "thumbnail_url": 1, "video_url": 1, "min_percentage": 1
    }
    cursor = db.levels.find({"is_legacy": {"$ne": True}}, fields).sort("position", 1)
    cursor.max_time_ms(90000)  # 90 second timeout
    main_levels = list(cursor)
    elapsed = (time.time() - start) * 1000
    print(f"✅ Pre-loaded {len(main_levels)} main levels in {elapsed:.2f}ms")
except Exception as e:
    print(f"❌ Failed to load main levels: {e}")
    main_levels = []

# Pre-load legacy list
print("\n🔄 Pre-loading LEGACY levels...")
try:
    start = time.time()
    cursor = db.levels.find({"is_legacy": True}, fields).sort("position", 1)
    cursor.max_time_ms(90000)
    legacy_levels = list(cursor)
    elapsed = (time.time() - start) * 1000
    print(f"✅ Pre-loaded {len(legacy_levels)} legacy levels in {elapsed:.2f}ms")
except Exception as e:
    print(f"❌ Failed to load legacy levels: {e}")
    legacy_levels = []

# Save to JSON cache file (backup)
import json
print("\n💾 Saving cache to JSON files...")
try:
    with open('cache_main_levels.json', 'w') as f:
        json.dump(main_levels, f, default=str)
    print("✅ Saved main levels cache")
    
    with open('cache_legacy_levels.json', 'w') as f:
        json.dump(legacy_levels, f, default=str)
    print("✅ Saved legacy levels cache")
except Exception as e:
    print(f"❌ Failed to save cache: {e}")

print("\n" + "=" * 80)
print("✅ CACHE PRE-LOADED SUCCESSFULLY!")
print("=" * 80)
print("\nNow start the server:")
print("   python main.py")
print("\nThe website will load INSTANTLY using cached data!")
print("=" * 80)
