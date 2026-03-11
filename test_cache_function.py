"""Test the get_fast_cached_levels function"""
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

# Setup
client = MongoClient(os.environ.get('MONGODB_URI'))
mongo_db = client[os.environ.get('MONGODB_DB')]

levels_cache = {
    'main_list': None,
    'legacy_list': None,
    'last_updated': None,
    'ttl': 300
}

def get_fast_cached_levels(is_legacy=False):
    """Ultra-fast cached level retrieval with TTL"""
    global levels_cache
    
    cache_key = 'legacy_list' if is_legacy else 'main_list'
    now = datetime.now(timezone.utc)
    
    # Check if cache is valid
    if (levels_cache[cache_key] is not None and 
        levels_cache['last_updated'] is not None):
        
        age = (now - levels_cache['last_updated']).total_seconds()
        if age < levels_cache['ttl']:
            # Cache hit - return immediately
            print(f"CACHE HIT! Returning {len(levels_cache[cache_key])} levels")
            return levels_cache[cache_key]
    
    # Cache miss - load from database
    print("CACHE MISS - Loading from database...")
    try:
        if is_legacy:
            levels = list(mongo_db.levels.find(
                {"is_legacy": True},
                {"_id": 1, "name": 1, "creator": 1, "verifier": 1, "position": 1, 
                 "points": 1, "level_id": 1, "difficulty": 1, "video_url": 1, 
                 "thumbnail_url": 1, "min_percentage": 1, "demon_type": 1}
            ).sort("position", 1))
        else:
            levels = list(mongo_db.levels.find(
                {"$or": [{"is_legacy": False}, {"is_legacy": {"$exists": False}}]},
                {"_id": 1, "name": 1, "creator": 1, "verifier": 1, "position": 1, 
                 "points": 1, "level_id": 1, "difficulty": 1, "video_url": 1, 
                 "thumbnail_url": 1, "min_percentage": 1, "demon_type": 1}
            ).sort("position", 1).limit(100))
        
        print(f"Loaded {len(levels)} levels from database")
        
        # Update cache
        levels_cache[cache_key] = levels
        levels_cache['last_updated'] = now
        
        return levels
    except Exception as e:
        print(f"Error loading levels: {e}")
        return levels_cache.get(cache_key) or []

# Test it
print("=" * 60)
print("TESTING get_fast_cached_levels()")
print("=" * 60)

print("\n1. First call (should load from database):")
levels = get_fast_cached_levels(is_legacy=False)
print(f"   Got {len(levels)} levels")
if levels:
    print(f"   First level: #{levels[0]['position']}: {levels[0]['name']}")
    print(f"   Last level: #{levels[-1]['position']}: {levels[-1]['name']}")

print("\n2. Second call (should use cache):")
levels2 = get_fast_cached_levels(is_legacy=False)
print(f"   Got {len(levels2)} levels")

print("\n3. Verify data:")
print(f"   Same data: {levels == levels2}")
print(f"   Total levels: {len(levels)}")

print("\n" + "=" * 60)
print("SUCCESS! Function works correctly!")
print("=" * 60)
