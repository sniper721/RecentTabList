import json
from datetime import datetime, timezone

# Load cache from file
print("Loading cache from file...")
try:
    with open('cache_main_levels.json', 'r') as f:
        cache_data = json.load(f)
        print(f"✅ Loaded {len(cache_data.get('levels', []))} levels from cache file")
        
        # Now we need to add code to main.py to load this on startup
        print("\n📝 Add this code to main.py after the levels_cache definition:")
        print("""
# Load cache from file on startup
try:
    import json
    with open('cache_main_levels.json', 'r') as f:
        cache_data = json.load(f)
        levels_cache['main_list'] = cache_data.get('levels', [])
        levels_cache['last_updated'] = datetime.now(timezone.utc)
        print(f"✅ Loaded {len(levels_cache['main_list'])} levels from cache file")
except Exception as e:
    print(f"⚠️ Could not load cache file: {e}")
""")
        
except Exception as e:
    print(f"❌ Error: {e}")
