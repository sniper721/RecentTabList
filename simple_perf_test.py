"""
Simple performance test - just count levels quickly
"""
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import time

load_dotenv()

mongodb_uri = os.environ.get('MONGODB_URI')
mongodb_db = os.environ.get('MONGODB_DB')

print("Quick level count test...")
start = time.time()

client= MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
db = client[mongodb_db]

# Test 1: Count with is_legacy != true
count = db.levels.count_documents({"is_legacy": {"$ne": True}})
elapsed = (time.time() - start) * 1000
print(f"✅ Main list count: {count} levels in {elapsed:.2f}ms")

# Test 2: Simple find with limit
start = time.time()
levels = list(db.levels.find({"is_legacy": {"$ne": True}}).sort("position", 1).limit(10))
elapsed = (time.time() - start) * 1000
print(f"✅ Quick fetch (10 levels): {len(levels)} in {elapsed:.2f}ms")
if levels:
    print(f"   First level: #{levels[0].get('position')} - {levels[0].get('name')}")

# Test 3: Full fetch
start = time.time()
levels = list(db.levels.find({"is_legacy": {"$ne": True}}).sort("position", 1))
elapsed = (time.time() - start) * 1000
print(f"✅ Full fetch: {len(levels)} levels in {elapsed:.2f}ms")

print("\nDone!")
