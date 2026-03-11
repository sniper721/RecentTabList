"""
Quick test to simulate what happens when you visit the website
"""
import time

print("="*80)
print("Simulating Website Visit")
print("="*80)

start = time.time()

# Import the app (this starts everything)
from main import app, levels_cache, mongo_manager

elapsed = time.time() - start

print(f"\n⏱️ App imported in {elapsed:.2f}s")
print(f"Main levels in cache: {len(levels_cache.get('main_list', []))}")
print(f"MongoDB connected: {mongo_manager.is_connected()}")

if len(levels_cache.get('main_list', [])) > 0:
    print("\n✅ CACHE HAS DATA - Site will load instantly!")
    print(f"   First level: {levels_cache['main_list'][0]['name']}")
    print(f"   Total levels: {len(levels_cache['main_list'])}")
else:
    print("\n⚠️ Cache is empty - Site will show 'Loading...' message")
    print("   Waiting for MongoDB to connect in background...")
    print("   This may take 30-90 seconds depending on connection")
    
    # Wait and check periodically
    for i in range(10):
        time.sleep(10)
        count = len(levels_cache.get('main_list', []))
        if count > 0:
            print(f"\n✅ After {((i+1)*10)}s: Cache now has {count} levels!")
            print(f"   Refresh browser to see levels")
            break
        else:
            print(f"   Still waiting... ({(i+1)*10}s elapsed)")
    
    if count == 0:
        print("\n⚠️ MongoDB didn't connect in 100 seconds")
        print("   Check your internet connection and MongoDB Atlas access")
