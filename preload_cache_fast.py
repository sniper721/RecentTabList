"""
FAST Cache Preloader with Progress Indicator
Optimized for slow MongoDB Atlas with visible progress and hard timeouts
"""
from pymongo import MongoClient, ASCENDING
from dotenv import load_dotenv
import os
import json
import time
from datetime import datetime, timezone
import sys

load_dotenv()

mongodb_uri = os.environ.get('MONGODB_URI')
mongodb_db_name = os.environ.get('MONGODB_DB', 'rtl_database')

print("="*80)
print("⚡ FAST Cache Preloader (with Progress)")
print("="*80)

# Optimized configuration with HARD timeouts
config = {
    'serverSelectionTimeoutMS': 60000,   # 1 minute max to find server
    'socketTimeoutMS': 90000,             # 90 seconds for socket ops
    'connectTimeoutMS': 60000,            # 1 minute for initial connection
    'maxPoolSize': 20,
    'minPoolSize': 5,
    'maxIdleTimeMS': 60000,
    'retryWrites': True,
    'retryReads': True,
    'tls': True,
    'tlsAllowInvalidCertificates': True,
    'tlsAllowInvalidHostnames': True,
    'connect': False,
}

def preload_cache():
    """Preload cache with progress indicators and timeouts"""
    
    total_start = time.time()
    
    try:
        print("\n🔧 Connecting to MongoDB Atlas...")
        connect_start = time.time()
        
        client = MongoClient(mongodb_uri, **config)
        
        # Test connection with SHORT timeout
        print("📡 Testing connection (timeout: 30s)...")
        client.admin.command('ping', maxTimeMS=30000)
        
        connect_time = time.time() - connect_start
        print(f"✅ Connected in {connect_time:.1f}s")
        
        db = client[mongodb_db_name]
        
        # Load main levels SEQUENTIALLY (more reliable than parallel for slow connections)
        main_levels = load_levels_with_progress(
            db, 
            {"is_legacy": {"$ne": True}}, 
            "Main levels",
            timeout_ms=90000
        )
        
        # Save main cache immediately
        if main_levels:
            save_cache('cache_main_levels.json', main_levels)
        
        # Load legacy levels
        legacy_levels = load_levels_with_progress(
            db, 
            {"is_legacy": True}, 
            "Legacy levels",
            timeout_ms=90000
        )
        
        # Save legacy cache
        if legacy_levels:
            save_cache('cache_legacy_levels.json', legacy_levels)
        
        total_time = time.time() - total_start
        
        print("\n" + "="*80)
        print("✅ CACHE PRELOAD COMPLETED")
        print("="*80)
        print(f"\n📊 Results:")
        print(f"   • Main levels: {len(main_levels)}")
        print(f"   • Legacy levels: {len(legacy_levels)}")
        print(f"   • Total cached: {len(main_levels) + len(legacy_levels)}")
        print(f"   • Total time: {total_time:.1f}s")
        print("\n✨ Ready to use: python main.py")
        print("="*80)
        
        client.close()
        return True
        
    except Exception as e:
        elapsed = time.time() - total_start
        print(f"\n❌ Preload failed after {elapsed:.1f}s: {e}")
        print("\n⚠️ Creating empty cache fallback...")
        
        # Create empty caches
        empty_cache = {
            'levels': [],
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'count': 0
        }
        
        with open('cache_main_levels.json', 'w', encoding='utf-8') as f:
            json.dump(empty_cache, f, indent=2)
        
        with open('cache_legacy_levels.json', 'w', encoding='utf-8') as f:
            json.dump(empty_cache, f, indent=2)
        
        print("✅ Empty cache files created")
        print("\n💡 Site will still work! Run: python main.py")
        print("   MongoDB will connect in background and auto-populate cache")
        
        return False

def load_levels_with_progress(db, query, label, timeout_ms=90000):
    """Load levels with progress indicator and strict timeout"""
    
    print(f"\n📊 Loading {label.lower()}...")
    start = time.time()
    
    try:
        # Minimal projection for speed
        cursor = db.levels.find(
            query,
            {
                "_id": 1,
                "name": 1,
                "creator": 1,
                "position": 1,
                "points": 1,
                "difficulty": 1,
                "level_id": 1,
                "thumbnail_url": 1,
            }
        ).sort("position", ASCENDING)
        
        # Set strict timeout
        cursor.max_time_ms(timeout_ms)
        
        # Show progress while loading
        levels = []
        last_count = 0
        last_update = start
        
        for level in cursor:
            levels.append(level)
            
            # Show progress every 50 levels or every 10 seconds
            now = time.time()
            if len(levels) % 50 == 0 or (now - last_update) > 10:
                elapsed = now - start
                print(f"   ⏳ Loaded {len(levels)} levels... ({elapsed:.1f}s)")
                last_update = now
        
        elapsed = time.time() - start
        print(f"   ✅ Loaded {len(levels)} {label.lower()} in {elapsed:.1f}s")
        
        return levels
        
    except Exception as e:
        elapsed = time.time() - start
        print(f"   ❌ Failed to load {label.lower()} after {elapsed:.1f}s: {e}")
        return []

def save_cache(filename, levels):
    """Save levels to cache file"""
    try:
        cache_data = {
            'levels': levels,
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'count': len(levels)
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        
        print(f"   💾 Saved {filename}")
        
    except Exception as e:
        print(f"   ❌ Failed to save {filename}: {e}")

if __name__ == "__main__":
    print("\n⏱️  MAXIMUM TIMEOUT: 5 minutes total")
    print("   If it takes longer, script will auto-fail with empty cache\n")
    
    # Set overall timeout
    import threading
    
    result = {'success': False}
    
    def run_preload():
        result['success'] = preload_cache()
    
    # Start preload in thread
    thread = threading.Thread(target=run_preload)
    thread.daemon = True
    thread.start()
    
    # Wait max 5 minutes
    thread.join(timeout=300)  # 5 minutes
    
    if thread.is_alive():
        print("\n\n⚠️ TIMEOUT: Preload took longer than 5 minutes")
        print("   Stopping and using empty cache fallback...")
        
        # Create empty caches
        empty_cache = {
            'levels': [],
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'count': 0
        }
        
        with open('cache_main_levels.json', 'w', encoding='utf-8') as f:
            json.dump(empty_cache, f, indent=2)
        
        with open('cache_legacy_levels.json', 'w', encoding='utf-8') as f:
            json.dump(empty_cache, f, indent=2)
        
        print("✅ Empty cache files created")
        print("\n💡 Just run: python main.py")
        print("   Site will start instantly and MongoDB will connect in background")
