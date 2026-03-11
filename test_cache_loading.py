"""
Quick test to verify cache loading works
"""
import json
import os

print("="*80)
print("CACHE VERIFICATION TEST")
print("="*80)

# Check if cache files exist
main_cache = 'cache_main_levels.json'
legacy_cache = 'cache_legacy_levels.json'

print(f"\n1. Checking cache files...")
print(f"   Main cache exists: {os.path.exists(main_cache)}")
print(f"   Legacy cache exists: {os.path.exists(legacy_cache)}")

# Load and verify main cache
if os.path.exists(main_cache):
    print(f"\n2. Loading {main_cache}...")
    try:
        with open(main_cache, 'r', encoding='utf-8') as f:
            data = json.load(f)
            levels = data.get('levels', [])
            print(f"   ✅ Loaded {len(levels)} levels from cache")
            
            if len(levels) > 0:
                print(f"   📊 First level:")
                print(f"      - Name: {levels[0].get('name', 'Unknown')}")
                print(f"      - Position: {levels[0].get('position', 'Unknown')}")
                print(f"      - Creator: {levels[0].get('creator', 'Unknown')}")
            else:
                print(f"   ⚠️ Cache file exists but contains NO levels!")
    except Exception as e:
        print(f"   ❌ Failed to load cache: {e}")
else:
    print(f"\n2. ⚠️ No cache file found - will need to load from database")

print("\n" + "="*80)
print("EXPECTED BEHAVIOR:")
print("="*80)
print("""
When you run 'python main.py', you should see:

1. Cache preload message (if files exist):
   "✅ Pre-loaded X main levels from cache"

2. Loading thread message:
   "📊 Loading all levels..."
   "🔍 Checking cache: X levels in memory"
   "📁 Cache file exists: True"
   
3. If cache has data:
   "✅ Using X cached levels instantly!"
   "🚀 All X levels are now live!"
   
4. Website shows ALL levels immediately!

If cache is empty or missing:
   "⏳ No cache available, waiting for MongoDB..."
   Then loads from database when MongoDB connects
""")

print("="*80)
print("Run: python main.py")
print("="*80)
