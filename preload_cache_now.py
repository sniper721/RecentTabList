"""
Preload cache files from database - run this once to create cache files
This will make the site load instantly on subsequent visits
"""
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import json
from datetime import datetime, timezone

print("="*80)
print("🚀 Preloading Cache Files for Instant Site Loading")
print("="*80)

# Load environment variables
load_dotenv()

uri = os.environ.get('MONGODB_URI')
db_name = os.environ.get('MONGODB_DB')

print(f"\n📡 Connecting to MongoDB...")
try:
    client = MongoClient(
        uri,
        tls=True,
        tlsAllowInvalidCertificates=True,
        serverSelectionTimeoutMS=10000
    )
    db = client[db_name]
    
    # Test connection
    client.admin.command('ping')
    print("✅ Connected to MongoDB successfully")
    
except Exception as e:
    print(f"❌ Connection failed: {e}")
    exit(1)

# Load main levels
print("\n📊 Loading MAIN levels (is_legacy: False)...")
start = datetime.now()

main_levels = list(db.levels.find(
    {"is_legacy": False},
    {
        "_id": 1,
        "name": 1,
        "creator": 1,
        "verifier": 1,
        "position": 1,
        "points": 1,
        "level_id": 1,
        "difficulty": 1,
        "thumbnail_url": 1,
        "video_url": 1,
        "min_percentage": 1
    }
).sort("position", 1))

elapsed = (datetime.now() - start).total_seconds()
print(f"✅ Loaded {len(main_levels)} main levels in {elapsed:.2f}s")

# Save to cache file
cache_data = {
    'levels': main_levels,
    'last_updated': datetime.now(timezone.utc).isoformat()
}

with open('cache_main_levels.json', 'w', encoding='utf-8') as f:
    json.dump(cache_data, f, ensure_ascii=False, indent=2, default=str)

print(f"💾 Saved to cache_main_levels.json ({len(main_levels)} levels)")

# Load legacy levels
print("\n📊 Loading LEGACY levels (is_legacy: True)...")
start = datetime.now()

legacy_levels = list(db.levels.find(
    {"is_legacy": True},
    {
        "_id": 1,
        "name": 1,
        "creator": 1,
        "verifier": 1,
        "position": 1,
        "points": 1,
        "level_id": 1,
        "difficulty": 1,
        "thumbnail_url": 1,
        "video_url": 1,
        "min_percentage": 1
    }
).sort("position", 1))

elapsed = (datetime.now() - start).total_seconds()
print(f"✅ Loaded {len(legacy_levels)} legacy levels in {elapsed:.2f}s")

# Save to cache file
cache_data = {
    'levels': legacy_levels,
    'last_updated': datetime.now(timezone.utc).isoformat()
}

with open('cache_legacy_levels.json', 'w', encoding='utf-8') as f:
    json.dump(cache_data, f, ensure_ascii=False, indent=2, default=str)

print(f"💾 Saved to cache_legacy_levels.json ({len(legacy_levels)} levels)")

client.close()

print("\n" + "="*80)
print("✨ CACHE PRELOADING COMPLETE!")
print("="*80)
print(f"\n📊 Summary:")
print(f"   • Main levels cached: {len(main_levels)}")
print(f"   • Legacy levels cached: {len(legacy_levels)}")
print(f"   • Total levels: {len(main_levels) + len(legacy_levels)}")
print(f"\n🎉 The website will now load INSTANTLY!")
print(f"   No more 'Loading...' message - levels appear immediately!")
print("="*80)
