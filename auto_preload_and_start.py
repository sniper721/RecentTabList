"""
Auto-preload cache when main.py starts - runs BEFORE Flask starts
This loads data in background so website is instant
"""
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import json
import time

load_dotenv()

mongodb_uri = os.environ.get('MONGODB_URI')
mongodb_db = os.environ.get('MONGODB_DB')

print("=" * 80)
print("AUTO-PRELOADING CACHE (Background Process)")
print("=" * 80)

def preload_cache():
    """Pre-load levels into JSON cache files"""
    try:
        # Connect with VERY long timeouts
        client= MongoClient(
            mongodb_uri,
            tls=True,
            tlsAllowInvalidCertificates=True,
            tlsAllowInvalidHostnames=True,
          serverSelectionTimeoutMS=30000,
            socketTimeoutMS=120000,  # 2 minutes!
            connectTimeoutMS=60000,
            maxPoolSize=5,
            minPoolSize=1,
          retryWrites=True,
          retryReads=True,
            directConnection=False,
            connect=False
        )
        
        db = client[mongodb_db]
        
        # Test connection
        db.command('ping')
        print("✅ Connected to MongoDB")
        
        # Load main levels
        print("\n🔄 Loading main levels...")
        start = time.time()
        fields = {
            "_id": 1, "name": 1, "creator": 1, "verifier": 1,
            "position": 1, "points": 1, "level_id": 1, "difficulty": 1,
            "thumbnail_url": 1, "video_url": 1, "min_percentage": 1
        }
        
        cursor = db.levels.find({"is_legacy": {"$ne": True}}, fields).sort("position", 1)
        cursor.max_time_ms(120000)  # 2 minute timeout
        main_levels = list(cursor)
        
        elapsed = (time.time() - start) * 1000
        print(f"✅ Loaded {len(main_levels)} main levels in {elapsed:.2f}ms")
        
        # Save to JSON
        with open('cache_main_levels.json', 'w') as f:
            json.dump(main_levels, f, default=str)
        print("💾 Saved cache_main_levels.json")
        
        # Load legacy levels
        print("\n🔄 Loading legacy levels...")
        start = time.time()
        cursor = db.levels.find({"is_legacy": True}, fields).sort("position", 1)
        cursor.max_time_ms(120000)
        legacy_levels = list(cursor)
        
        elapsed = (time.time() - start) * 1000
        print(f"✅ Loaded {len(legacy_levels)} legacy levels in {elapsed:.2f}ms")
        
        # Save to JSON
        with open('cache_legacy_levels.json', 'w') as f:
            json.dump(legacy_levels, f, default=str)
        print("💾 Saved cache_legacy_levels.json")
        
        print("\n" + "=" * 80)
        print("✅ CACHE PRE-LOADED SUCCESSFULLY!")
        print("=" * 80)
        print("\nStarting server now with cached data...")
        
        # Now start main.py
        import subprocess
        subprocess.run(['python', 'main.py'])
        
    except Exception as e:
        print(f"\n❌ Pre-load failed: {e}")
        print("\n⚠️  Starting server anyway (without cache)...")
        import subprocess
        subprocess.run(['python', 'main.py'])

# Run pre-load
preload_cache()
