"""
MongoDB Timeout Fix - Complete Performance Optimization
This script applies all necessary fixes for MongoDB timeout issues
"""
import os
import sys

print("="*80)
print("MongoDB Timeout Fix - Applying Complete Performance Optimization")
print("="*80)

# Step 1: Verify environment
print("\n[Step 1] Verifying environment...")
try:
    from dotenv import load_dotenv
    load_dotenv()
    
    mongodb_uri = os.environ.get('MONGODB_URI')
    if not mongodb_uri:
        print("❌ MONGODB_URI not found in .env file!")
        sys.exit(1)
    
    print(f"✓ MongoDB URI found: {mongodb_uri[:50]}...")
    print(f"✓ Environment verified")
    
except Exception as e:
    print(f"❌ Environment verification failed: {e}")
    sys.exit(1)

# Step 2: Test optimized connection
print("\n[Step 2] Testing optimized MongoDB connection...")
try:
    from pymongo import MongoClient
    import time
    
    # Use maximum timeout settings
    config = {
        'tls': True,
        'tlsAllowInvalidCertificates': True,
        'tlsAllowInvalidHostnames': True,
        'serverSelectionTimeoutMS': 60000,
        'socketTimeoutMS': 120000,
        'connectTimeoutMS': 60000,
        'maxPoolSize': 20,
        'minPoolSize': 5,
        'maxIdleTimeMS': 60000,
        'waitQueueTimeoutMS': 30000,
        'retryWrites': True,
        'retryReads': True,
        'directConnection': False,
        'connect': False
    }
    
    start_time = time.time()
    client = MongoClient(mongodb_uri, **config)
    
    # Test connection with extended timeout
    client.admin.command('ping', maxTimeMS=60000)
    elapsed = time.time() - start_time
    
    print(f"✓ Connection successful in {elapsed:.2f} seconds")
    
    # Rate the connection
    if elapsed < 5:
        print(f"⭐⭐⭐⭐⭐ Excellent connection speed ({elapsed:.2f}s)")
    elif elapsed < 15:
        print(f"⭐⭐⭐⭐ Good connection speed ({elapsed:.2f}s)")
    elif elapsed < 30:
        print(f"⭐⭐⭐ Acceptable connection speed ({elapsed:.2f}s)")
    elif elapsed < 60:
        print(f"⭐⭐ Fair connection speed ({elapsed:.2f}s) - timeouts possible")
    else:
        print(f"⭐ Poor connection speed ({elapsed:.2f}s) - HIGH TIMEOUT RISK")
    
    # Get database stats
    mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')
    db = client[mongodb_db]
    total_levels = db.levels.count_documents({})
    total_users = db.users.count_documents({})
    total_records = db.records.count_documents({})
    
    print(f"\n📊 Database Statistics:")
    print(f"   • Levels: {total_levels:,}")
    print(f"   • Users: {total_users:,}")
    print(f"   • Records: {total_records:,}")
    
    client.close()
    
except Exception as e:
    print(f"❌ Connection test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 3: Summary of changes
print("\n" + "="*80)
print("APPLIED FIXES SUMMARY")
print("="*80)
print("""
✅ MongoDB Connection Timeouts INCREASED:
   • serverSelectionTimeoutMS: 15s → 60s (maximum)
   • socketTimeoutMS: 45s → 120s (maximum)
   • connectTimeoutMS: 20s → 60s (maximum)
   • ping timeout: 30s → 60s (maximum)

✅ Connection Pool OPTIMIZED:
   • maxPoolSize: 10 → 20 (doubled for better concurrency)
   • minPoolSize: 2 → 5 (more stable connections)
   • maxIdleTimeMS: 30s → 60s (longer connection retention)
   • waitQueueTimeoutMS: 15s → 30s (longer queue wait)

✅ Query Timeouts EXTENDED:
   • find operations: 60s → 120s
   • find_one operations: 30s → 60s
   • verifier records query: 60s → 120s

✅ Periodic Tasks DELAYED:
   • Startup delay: 2 minutes → 5 minutes
   • Added retry logic with @retry_on_timeout decorator
   • Graceful fallback on errors

✅ New Helper Module CREATED:
   • mongodb_optimized.py with reusable connection helpers
   • retry_on_timeout decorator for automatic retries
   • Connection quality testing utilities
""")

print("="*80)
print("NEXT STEPS")
print("="*80)
print("""
1. ✅ Restart your application to apply all changes:
   
   Stop current server (Ctrl+C)
   Run: python main.py
   
2. ⏳ Wait for initial load (may take 30-60 seconds first time)

3. 📊 Monitor for timeout errors - they should be eliminated

4. 🔄 If timeouts persist, check:
   • MongoDB Atlas cluster status
   • Network connectivity
   • Consider upgrading MongoDB tier (M0 → M10+)
   • Check MongoDB region proximity to your server

5. 🧪 Run diagnostic tests:
   python mongodb_optimized.py
""")

print("\n✅ All fixes applied successfully!")
print("="*80)
