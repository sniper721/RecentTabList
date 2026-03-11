"""
Create optimized indexes for better query performance
"""
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import time

# Load environment variables
load_dotenv()

# Get MongoDB configuration
mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

print("=" * 80)
print("Creating Database Indexes for Performance")
print("=" * 80)

# Connect to MongoDB
mongo_client= MongoClient(
    mongodb_uri,
    tls=True,
    tlsAllowInvalidCertificates=True,
    tlsAllowInvalidHostnames=True,
    serverSelectionTimeoutMS=30000,
    socketTimeoutMS=45000,
    connectTimeoutMS=30000,
    maxPoolSize=10,
    minPoolSize=2,
    directConnection=False,
    connect=False
)

db = mongo_client[mongodb_db]

print("\n📊 Creating indexes on 'levels' collection...")

try:
    # Drop existing indexes first (except _id_)
    print("\nDropping old indexes...")
    try:
        indexes = db.levels.list_indexes()
        for index in indexes:
            if index['name'] != '_id_':
                db.levels.drop_index(index['name'])
                print(f"  Dropped index: {index['name']}")
    except Exception as e:
        print(f"Note: {e}")
    
    # Create new optimized indexes with error handling
    print("\nCreating new indexes...")
    
    # Index for main list query (most important!)
    try:
        print("  1. Main list index (is_legacy + position)...")
        start = time.time()
        db.levels.create_index([("is_legacy", 1), ("position", 1)], name="isLegacy_position_idx")
        print(f"     ✅ Created in {(time.time() - start)*1000:.2f}ms")
    except Exception as e:
        print(f"     ⚠️  Skipped (may already exist): {e}")
    
    # Index for position-only queries
    try:
        print("  2. Position index...")
        start = time.time()
        db.levels.create_index([("position", 1)], name="position_idx")
        print(f"     ✅ Created in {(time.time() - start)*1000:.2f}ms")
    except Exception as e:
        print(f"     ⚠️  Skipped: {e}")
    
    # Index for level_id queries
    try:
        print("  3. Level ID index...")
        start = time.time()
        db.levels.create_index([("level_id", 1)], name="levelId_idx")
        print(f"     ✅ Created in {(time.time() - start)*1000:.2f}ms")
    except Exception as e:
        print(f"     ⚠️  Skipped: {e}")
    
    # Compound index for common queries
    try:
        print("  4. Compound index (is_legacy + position + level_id)...")
        start = time.time()
        db.levels.create_index([("is_legacy", 1), ("position", 1), ("level_id", 1)], name="isLegacy_pos_levelId_idx")
        print(f"     ✅ Created in {(time.time() - start)*1000:.2f}ms")
    except Exception as e:
        print(f"     ⚠️  Skipped: {e}")
    
    print("\n✅ Index optimization complete!")
    
    # List all indexes
    print("\n📋 Current indexes:")
    for idx in db.levels.list_indexes():
        print(f"   - {idx['name']}: {idx['key']}")
    
except Exception as e:
    print(f"\n❌ Error creating indexes: {e}")
    import traceback
    traceback.print_exc()

# Test query performance after indexing
print("\n\n📊 Testing query performance after indexing...")
start = time.time()
result = list(db.levels.find({"is_legacy": {"$ne": True}}).sort("position", 1))
elapsed = (time.time() - start) * 1000
print(f"✅ Main list query: {len(result)} levels in {elapsed:.2f}ms")

start = time.time()
result = list(db.levels.find({"is_legacy": True}).sort("position", 1))
elapsed = (time.time() - start) * 1000
print(f"✅ Legacy query: {len(result)} levels in {elapsed:.2f}ms")

print("\n" + "=" * 80)
print("Index creation complete!")
print("=" * 80)
