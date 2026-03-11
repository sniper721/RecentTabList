"""Test instant loading on startup"""
import time
start = time.time()

print("Starting import...")
from main import levels_cache, mongo_manager

elapsed = time.time() - start
print(f"\n⏱️ Import completed in {elapsed:.2f}s")
print(f"Main levels cached: {len(levels_cache.get('main_list', []))}")
print(f"Legacy levels cached: {len(levels_cache.get('legacy_list', []))}")
print(f"MongoDB connected: {mongo_manager.is_connected()}")

if len(levels_cache.get('main_list', [])) > 0:
    print("\n✅ SUCCESS - Levels loaded instantly!")
    print(f"First level: {levels_cache['main_list'][0]['name']}")
else:
    print("\n⚠️ Cache still empty")
