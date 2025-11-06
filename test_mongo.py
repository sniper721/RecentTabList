#!/usr/bin/env python3
"""Quick MongoDB connection test"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

mongodb_uri = os.environ.get('MONGODB_URI')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

print("🔍 Testing MongoDB connection...")
print(f"URI: {mongodb_uri[:50]}...")
print(f"Database: {mongodb_db}")

try:
    # Create optimized client
    client = MongoClient(
        mongodb_uri,
        serverSelectionTimeoutMS=5000,
        socketTimeoutMS=5000,
        connectTimeoutMS=5000,
        maxPoolSize=1,  # Single connection for test
        retryWrites=True
    )
    
    db = client[mongodb_db]
    
    print("⏱️  Testing connection...")
    start_time = time.time()
    
    # Test ping
    result = client.admin.command('ping', maxTimeMS=3000)
    ping_time = time.time() - start_time
    
    print(f"✅ Ping successful! ({ping_time:.2f}s)")
    
    # Test database access
    start_time = time.time()
    level_count = db.levels.count_documents({}, maxTimeMS=3000)
    count_time = time.time() - start_time
    
    print(f"✅ Database access successful! ({count_time:.2f}s)")
    print(f"📊 Found {level_count} levels in database")
    
    # Test a quick query
    start_time = time.time()
    sample_level = db.levels.find_one({}, {"name": 1, "creator": 1}, max_time_ms=3000)
    query_time = time.time() - start_time
    
    if sample_level:
        print(f"✅ Query successful! ({query_time:.2f}s)")
        print(f"📝 Sample level: {sample_level.get('name', 'Unknown')} by {sample_level.get('creator', 'Unknown')}")
    else:
        print("⚠️  No levels found in database")
    
    client.close()
    print("🎉 All tests passed! MongoDB connection is working.")
    
except Exception as e:
    print(f"❌ Connection failed: {e}")
    import traceback
    traceback.print_exc()