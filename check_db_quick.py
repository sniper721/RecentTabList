"""
Quick diagnostic script to check MongoDB connection and level data
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
print("MongoDB Connection Diagnostic")
print("=" * 80)
print(f"URI: {mongodb_uri[:50]}...")
print(f"Database: {mongodb_db}")
print("=" * 80)

# Try to connect with different timeout settings
timeouts = [5000, 10000, 30000, 60000]  # Different timeout values to test

for timeout_ms in timeouts:
    print(f"\nTrying with serverSelectionTimeoutMS={timeout_ms}...")
    try:
        mongo_client= MongoClient(
            mongodb_uri,
            tls=True,
            tlsAllowInvalidCertificates=True,
            tlsAllowInvalidHostnames=True,
            serverSelectionTimeoutMS=timeout_ms,
            socketTimeoutMS=45000,
            connectTimeoutMS=30000,
            maxPoolSize=10,
            minPoolSize=2,
            directConnection=False,
            connect=False
        )
        
        # Test connection
        start_time = time.time()
        mongo_client.admin.command('ping')
        ping_time = (time.time() - start_time) * 1000
        
        print(f"✅ Connection successful! Ping time: {ping_time:.2f}ms")
        
        # Check database
        db = mongo_client[mongodb_db]
        
        # Count levels
        print("\nChecking collections...")
        collections = db.list_collection_names()
        print(f"Available collections: {collections}")
        
        if 'levels' in collections:
            total_levels = db.levels.count_documents({})
            main_levels = db.levels.count_documents({"is_legacy": {"$ne": True}})
            legacy_levels = db.levels.count_documents({"is_legacy": True})
            
            print(f"\n📊 Level Statistics:")
            print(f"   Total levels: {total_levels}")
            print(f"   Main list levels: {main_levels}")
            print(f"   Legacy levels: {legacy_levels}")
            
            # Sample some levels
            print(f"\n📋 Sample Main List Levels:")
            sample_levels = list(db.levels.find({"is_legacy": {"$ne": True}}).sort("position", 1).limit(5))
            for level in sample_levels:
                print(f"   #{level.get('position')} - {level.get('name')} by {level.get('creator')}")
            
            # Check for any levels at all
            first_level = db.levels.find_one({"is_legacy": {"$ne": True}})
            if not first_level:
                print("\n⚠️  WARNING: No main list levels found!")
                # Check if there are ANY levels
                any_level = db.levels.find_one()
                if any_level:
                    print(f"Found level but different structure: {any_level}")
                else:
                    print("ERROR: No levels in database at all!")
        else:
            print("\n⚠️  WARNING: 'levels' collection not found!")
        
        break
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        if timeout_ms == timeouts[-1]:
            print("\nAll timeout values failed. Check your MongoDB URI and network connection.")
            print("\nPossible issues:")
            print("1. MongoDB Atlas cluster is paused or stopped")
            print("2. Network connectivity issues")
            print("3. Incorrect MongoDB URI")
            print("4. IP address not whitelisted in MongoDB Atlas")
        continue

print("\n" + "=" * 80)
print("Diagnostic complete")
print("=" * 80)
