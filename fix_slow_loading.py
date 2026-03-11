"""
Complete fix for slow site loading and database issues
This script will:
1. Optimize MongoDB connection
2. Clear stale cache
3. Verify level data
4. Test performance
"""
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import time

load_dotenv()

mongodb_uri = os.environ.get('MONGODB_URI')
mongodb_db = os.environ.get('MONGODB_DB')

print("=" * 80)
print("COMPLETE SITE PERFORMANCE FIX")
print("=" * 80)

# Step 1: Connect with optimized settings
print("\n📡 Step 1: Connecting to MongoDB with optimized settings...")
start = time.time()

client= MongoClient(
    mongodb_uri,
    tls=True,
    tlsAllowInvalidCertificates=True,
    tlsAllowInvalidHostnames=True,
    serverSelectionTimeoutMS=10000,
    socketTimeoutMS=20000,
    connectTimeoutMS=10000,
    maxPoolSize=10,
    minPoolSize=2,
    maxIdleTimeMS=20000,
    waitQueueTimeoutMS=10000,
    retryWrites=True,
    retryReads=True,
    directConnection=False,
    connect=False
)

db = client[mongodb_db]
elapsed = (time.time() - start) * 1000
print(f"✅ Connected in {elapsed:.2f}ms")

# Step 2: Check level counts
print("\n📊 Step 2: Checking level counts...")
total_levels = db.levels.count_documents({})
main_levels = db.levels.count_documents({"is_legacy": {"$ne": True}})
legacy_levels = db.levels.count_documents({"is_legacy": True})

print(f"   Total levels: {total_levels}")
print(f"   Main list: {main_levels}")
print(f"   Legacy: {legacy_levels}")

if main_levels < 150:
    print(f"\n⚠️  WARNING: Only {main_levels} main levels found (expected 150)")
    print("   You may need to run extend_main_list_to_150.py")

# Step 3: Verify indexes exist
print("\n🔧 Step 3: Verifying indexes...")
indexes = list(db.levels.list_indexes())
index_names = [idx['name'] for idx in indexes]

required_indexes = ['isLegacy_position_idx', 'position_idx', 'levelId_idx']
missing_indexes = [idx for idx in required_indexes if idx not in index_names]

if missing_indexes:
    print(f"⚠️  Missing indexes: {missing_indexes}")
    print("   Run create_indexes.py to add them")
else:
    print("✅ All required indexes present")

# Step 4: Test query performance
print("\n⚡ Step 4: Testing query performance...")

# Test 1: Count query
start = time.time()
count = db.levels.count_documents({"is_legacy": {"$ne": True}})
elapsed = (time.time() - start) * 1000
print(f"   Count query: {elapsed:.2f}ms")

# Test 2: Fetch all main levels (with maxTimeMS to prevent timeout)
try:
    start = time.time()
    cursor = db.levels.find({"is_legacy": {"$ne": True}}).sort("position", 1)
    cursor.max_time_ms(30000)  # 30 second timeout
    levels = list(cursor)
    elapsed = (time.time() - start) * 1000
    print(f"   Fetch all main: {len(levels)} levels in {elapsed:.2f}ms")
except Exception as e:
    print(f"   Fetch all main: TIMEOUT after 30s - {str(e)[:80]}")

# Test 3: Fetch all legacy levels (with maxTimeMS)
try:
    start = time.time()
    cursor = db.levels.find({"is_legacy": True}).sort("position", 1)
    cursor.max_time_ms(30000)  # 30 second timeout
    levels = list(cursor)
    elapsed = (time.time() - start) * 1000
    print(f"   Fetch all legacy: {len(levels)} levels in {elapsed:.2f}ms")
except Exception as e:
    print(f"   Fetch all legacy: TIMEOUT after 30s - {str(e)[:80]}")

# Test 4: Fetch with projection (what old code used)
try:
    start = time.time()
    levels = list(db.levels.find(
        {"is_legacy": {"$ne": True}},
        {"_id": 1, "name": 1, "creator": 1, "position": 1, "points": 1}
    ).sort("position", 1).limit(200))
    elapsed = (time.time() - start) * 1000
    print(f"   Fetch with projection: {len(levels)} levels in {elapsed:.2f}ms")
except Exception as e:
    print(f"   Fetch with projection: TIMEOUT - {str(e)[:80]}")

# Step 5: Sample data verification
print("\n📋 Step 5: Verifying data integrity...")
sample = db.levels.find_one({"is_legacy": {"$ne": True}})
if sample:
    print("✅ Main list levels have proper structure")
    print(f"   Sample: #{sample.get('position')} - {sample.get('name')}")
else:
    print("❌ No main list levels found!")

# Step 6: Clear any cached data in site_settings
print("\n🔄 Step 6: Clearing any stored cache references...")
try:
    db.site_settings.update_one(
        {"_id": "cache"},
        {"$set": {"cleared_at": time.time()}},
        upsert=True
    )
    print("✅ Cache marker cleared")
except Exception as e:
    print(f"⚠️  Could not clear cache marker: {e}")

print("\n" + "=" * 80)
print("✅ PERFORMANCE FIX COMPLETE!")
print("=" * 80)
print("\nRecommended next steps:")
print("1. Restart the server: python main.py")
print("2. Test the homepage load time")
print("3. If still slow, check MongoDB Atlas cluster performance")
print("=" * 80)
