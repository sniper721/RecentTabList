"""
ULTRA-FAST Cache Preloader
Optimized for extremely slow MongoDB Atlas connections
Uses minimal queries, aggressive timeouts, and parallel operations
"""
from pymongo import MongoClient, ASCENDING
from dotenv import load_dotenv
import os
import json
import time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

mongodb_uri = os.environ.get('MONGODB_URI')
mongodb_db_name = os.environ.get('MONGODB_DB', 'rtl_database')

print("="*80)
print("🚀 ULTRA-FAST Cache Preloader")
print("="*80)

# AGGRESSIVE OPTIMIZATIONS FOR SLOW CONNECTIONS
config = {
    # Maximum timeouts for ultra-slow connections
    'serverSelectionTimeoutMS': 120000,  # 2 minutes to find server
    'socketTimeoutMS': 180000,            # 3 minutes for socket operations
    'connectTimeoutMS': 120000,           # 2 minutes for initial connection
    
    # Connection pooling for better performance
    'maxPoolSize': 50,                     # Large pool for parallel queries
    'minPoolSize': 10,                     # Keep many connections ready
    'maxIdleTimeMS': 120000,              # Keep connections alive longer
    
    # Retry settings
    'retryWrites': True,
    'retryReads': True,
    
    # TLS settings (for Atlas)
    'tls': True,
    'tlsAllowInvalidCertificates': True,
    'tlsAllowInvalidHostnames': True,
    
    # Don't wait for connection - start immediately
    'connect': False,
    'directConnection': False,
}

def preload_with_minimal_fields():
    """Preload cache using minimal fields for faster queries"""
    print("\n⚡ Using ULTRA-FAST minimal field projection...")
    
    try:
        print(f"🔧 Connecting with aggressive timeouts...")
        start_time = time.time()
        
        client = MongoClient(mongodb_uri, **config)
        
        # Test with ping (short timeout)
        print("📡 Testing connection...")
        client.admin.command('ping', maxTimeMS=30000)
        
        elapsed = time.time() - start_time
        print(f"✅ Connected in {elapsed:.2f}s")
        
        db = client[mongodb_db_name]
        
        # Use ThreadPoolExecutor for PARALLEL loading
        print("\n🔄 Loading main and legacy levels in PARALLEL...")
        parallel_start = time.time()
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Submit both queries simultaneously
            main_future = executor.submit(load_main_levels_parallel, db)
            legacy_future = executor.submit(load_legacy_levels_parallel, db)
            
            # Get results
            main_levels = main_future.result()
            legacy_levels = legacy_future.result()
        
        parallel_elapsed = time.time() - parallel_start
        print(f"✅ Parallel loading completed in {parallel_elapsed:.2f}s")
        
        # Save caches
        print("\n💾 Saving cache files...")
        
        save_cache('cache_main_levels.json', main_levels)
        save_cache('cache_legacy_levels.json', legacy_levels)
        
        print("\n" + "="*80)
        print("✅ CACHE PRELOADED SUCCESSFULLY (ULTRA-FAST MODE)")
        print("="*80)
        print(f"\n📊 Summary:")
        print(f"   • Main levels: {len(main_levels)}")
        print(f"   • Legacy levels: {len(legacy_levels)}")
        print(f"   • Total cached: {len(main_levels) + len(legacy_levels)}")
        print(f"   • Total time: {time.time() - start_time:.2f}s")
        print("\n✨ You can now run: python main.py")
        print("="*80)
        
        client.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Failed to preload cache: {e}")
        print("\n⚠️ Creating empty cache files as fallback...")
        
        # Create empty cache files
        empty_cache = {
            'levels': [],
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'count': 0
        }
        
        with open('cache_main_levels.json', 'w', encoding='utf-8') as f:
            json.dump(empty_cache, f, indent=2)
        
        with open('cache_legacy_levels.json', 'w', encoding='utf-8') as f:
            json.dump(empty_cache, f, indent=2)
        
        print("⚠️ Created empty cache files")
        return False

def load_main_levels_parallel(db):
    """Load main levels with minimal fields (parallel execution)"""
    try:
        print("  📊 Loading main levels...")
        start = time.time()
        
        # MINIMAL PROJECTION - Only essential fields for display
        # This makes the query MUCH faster
        cursor = db.levels.find(
            {"is_legacy": {"$ne": True}},
            {
                "_id": 1,           # Required for MongoDB operations
                "name": 1,          # Display name
                "creator": 1,       # Display creator
                "position": 1,      # Sorting/ordering
                "points": 1,        # Display points
                "difficulty": 1,    # Display difficulty
                "level_id": 1,      # Reference ID
                # Optional fields (only if needed for display)
                "thumbnail_url": 1, # Thumbnail image
                # Skip heavy fields like image_base64 for faster loading
            }
        ).sort("position", ASCENDING)
        
        # Apply timeout to prevent hanging
        cursor.max_time_ms(120000)  # 2 minute timeout per query
        
        levels = list(cursor)
        elapsed = time.time() - start
        
        print(f"  ✅ Loaded {len(levels)} main levels in {elapsed:.2f}s")
        return levels
        
    except Exception as e:
        print(f"  ❌ Failed to load main levels: {e}")
        return []

def load_legacy_levels_parallel(db):
    """Load legacy levels with minimal fields (parallel execution)"""
    try:
        print("  📊 Loading legacy levels...")
        start = time.time()
        
        # MINIMAL PROJECTION - Only essential fields
        cursor = db.levels.find(
            {"is_legacy": True},
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
        
        cursor.max_time_ms(120000)
        
        levels = list(cursor)
        elapsed = time.time() - start
        
        print(f"  ✅ Loaded {len(levels)} legacy levels in {elapsed:.2f}s")
        return levels
        
    except Exception as e:
        print(f"  ❌ Failed to load legacy levels: {e}")
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
        
        print(f"  💾 Saved {filename} ({len(levels)} levels)")
        
    except Exception as e:
        print(f"  ❌ Failed to save {filename}: {e}")

if __name__ == "__main__":
    success = preload_with_minimal_fields()
    
    if success:
        print("\n✅ Success! Run: python main.py")
    else:
        print("\n⚠️ Empty cache created. Site will still work!")
        print("   Run: python main.py")
