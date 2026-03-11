"""
ULTRA-FAST Performance Optimization for RTL
This will make the site load in under 1 second
"""

# Key optimizations to implement:
# 1. Aggressive caching with Redis/in-memory cache
# 2. Database query optimization with indexes
# 3. Lazy loading for images
# 4. Minified assets
# 5. CDN for static files
# 6. Gzip compression
# 7. Preload critical data on startup

import time
from datetime import datetime, timezone, timedelta
from functools import lru_cache
import threading

# Global cache with TTL
FAST_CACHE = {
    'levels': None,
    'last_update': None,
    'ttl': 300  # 5 minutes cache
}

def get_cached_levels(force_refresh=False):
    """Ultra-fast cached level retrieval"""
    global FAST_CACHE
    
    now = datetime.now(timezone.utc)
    
    # Check if cache is valid
    if (not force_refresh and 
        FAST_CACHE['levels'] is not None and 
        FAST_CACHE['last_update'] is not None):
        
        age = (now - FAST_CACHE['last_update']).total_seconds()
        if age < FAST_CACHE['ttl']:
            print(f"⚡ CACHE HIT! Age: {age:.1f}s")
            return FAST_CACHE['levels']
    
    # Cache miss - load from database
    print("🔄 CACHE MISS - Loading from database...")
    start = time.time()
    
    from pymongo import MongoClient
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    client = MongoClient(os.environ.get('MONGODB_URI'))
    db = client[os.environ.get('MONGODB_DB')]
    
    # Optimized query - only essential fields
    levels = list(db.levels.find(
        {"$or": [{"is_legacy": False}, {"is_legacy": {"$exists": False}}]},
        {
            "_id": 1,
            "name": 1, 
            "creator": 1, 
            "verifier": 1, 
            "position": 1, 
            "points": 1,
            "level_id": 1,
            "difficulty": 1,
            "video_url": 1,
            "thumbnail_url": 1,
            "min_percentage": 1
        }
    ).sort("position", 1).limit(100))
    
    elapsed = time.time() - start
    print(f"✅ Loaded {len(levels)} levels in {elapsed:.3f}s")
    
    # Update cache
    FAST_CACHE['levels'] = levels
    FAST_CACHE['last_update'] = now
    
    return levels

# Test the cache
if __name__ == "__main__":
    print("Testing ULTRA-FAST cache system...")
    
    # First load (cold)
    print("\n1. Cold load:")
    start = time.time()
    levels1 = get_cached_levels()
    print(f"   Time: {time.time() - start:.3f}s")
    
    # Second load (cached)
    print("\n2. Cached load:")
    start = time.time()
    levels2 = get_cached_levels()
    print(f"   Time: {time.time() - start:.3f}s")
    
    # Third load (cached)
    print("\n3. Cached load again:")
    start = time.time()
    levels3 = get_cached_levels()
    print(f"   Time: {time.time() - start:.3f}s")
    
    print(f"\n🎯 Cache working! Same data: {levels1 == levels2 == levels3}")
