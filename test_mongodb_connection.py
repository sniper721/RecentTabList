#!/usr/bin/env python3
"""
Test MongoDB connection with new timeout settings
"""

import os
import time
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB configuration
mongodb_uri = os.environ.get('MONGODB_URI')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

print("=" * 70)
print("Testing MongoDB Connection with New Timeout Settings")
print("=" * 70)
print(f"URI: {mongodb_uri[:50]}...")
print(f"Database: {mongodb_db}")
print()

try:
    # Test with NEW timeout settings (matching main.py)
    print("🔍 Attempting connection with increased timeouts...")
    start_time = time.time()
    
    client = MongoClient(
        mongodb_uri,
        tls=True,
        tlsAllowInvalidCertificates=True,
        tlsAllowInvalidHostnames=True,
        serverSelectionTimeoutMS=30000,     # 30 seconds
        socketTimeoutMS=45000,              # 45 seconds
        connectTimeoutMS=30000,             # 30 seconds
        maxPoolSize=10,
        minPoolSize=2,
        maxIdleTimeMS=45000,
        waitQueueTimeoutMS=15000,
        retryWrites=True,
        retryReads=True,
        directConnection=False,
        connect=False
    )
    
    db = client[mongodb_db]
    
    # Test connection
    print("⏱️  Testing connection with ping...")
    client.admin.command('ping', maxTimeMS=30000)
    
    connection_time = time.time() - start_time
    print(f"✅ SUCCESS! Connected in {connection_time:.2f} seconds")
    print()
    
    # Test query performance
    print("📊 Testing database queries...")
    query_start = time.time()
    
    level_count = db.levels.count_documents({})
    user_count = db.users.count_documents({})
    record_count = db.records.count_documents({})
    
    query_time = time.time() - query_start
    
    print(f"✅ Database stats:")
    print(f"   - Levels: {level_count:,}")
    print(f"   - Users: {user_count:,}")
    print(f"   - Records: {record_count:,}")
    print(f"   - Query time: {query_time:.2f}s")
    print()
    
    # Test a sample query with timeout
    print("🔍 Testing level query with timeout...")
    query_start = time.time()
    
    levels = list(db.levels.find({}, maxTimeMS=60000).limit(5))
    
    query_time = time.time() - query_start
    print(f"✅ Sample query completed in {query_time:.2f}s")
    print(f"   Retrieved {len(levels)} levels")
    print()
    
    print("=" * 70)
    print("✅ ALL TESTS PASSED - MongoDB connection is working!")
    print("=" * 70)
    print()
    print("💡 If the website is still slow, the issue might be:")
    print("   1. Network latency to MongoDB Atlas servers")
    print("   2. MongoDB Atlas free tier throttling")
    print("   3. IP address whitelist restrictions")
    print()
    print("🔧 Next steps:")
    print("   - Check MongoDB Atlas network access settings")
    print("   - Ensure your IP is whitelisted (0.0.0.0/0 for allow all)")
    print("   - Consider upgrading MongoDB Atlas if on free tier")
    
except Exception as e:
    print(f"❌ FAILED: {e}")
    print()
    print("🔍 Troubleshooting steps:")
    print("   1. Check MongoDB Atlas cluster status")
    print("   2. Verify network access whitelist in MongoDB Atlas")
    print("   3. Check if your IP address is blocked")
    print("   4. Try restarting MongoDB Atlas cluster")
    import traceback
    traceback.print_exc()
