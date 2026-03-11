"""
Test MongoDB Atlas Connection
This script tests if you can connect to your MongoDB Atlas cluster
"""

import os
from dotenv import load_dotenv
from pymongo import MongoClient
import time

# Load environment variables
load_dotenv()

mongodb_uri = os.environ.get('MONGODB_URI')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

print("=" * 80)
print("🔍 TESTING MONGODB ATLAS CONNECTION")
print("=" * 80)
print(f"\n📡 Connection String: {mongodb_uri[:50]}...")
print(f"📊 Database Name: {mongodb_db}")
print()

try:
    print("⏳ Connecting to MongoDB Atlas...")
    start_time = time.time()
    
    # Connect with longer timeouts
    client = MongoClient(
        mongodb_uri,
        serverSelectionTimeoutMS=60000,  # 60 seconds
        socketTimeoutMS=120000,
        connectTimeoutMS=60000,
        maxPoolSize=10,
        tls=True,
        tlsAllowInvalidCertificates=False
    )
    
    # Test connection
    print("📡 Testing connection...")
    client.admin.command('ping')
    
    elapsed = time.time() - start_time
    print(f"\n✅ SUCCESS! Connected in {elapsed:.2f} seconds!")
    
    # Get cluster info
    print("\n📊 CLUSTER INFORMATION:")
    try:
        is_master = client.admin.command('isMaster')
        print(f"   • Host: {is_master.get('me', 'Unknown')}")
        
        build_info = client.admin.command('buildInfo')
        print(f"   • MongoDB Version: {build_info.get('version', 'Unknown')}")
        
        # List databases
        print("\n📁 AVAILABLE DATABASES:")
        databases = client.list_database_names()
        for db_name in sorted(databases):
            print(f"   - {db_name}")
        
        # Check RTL database
        if mongodb_db in databases:
            db = client[mongodb_db]
            collections = db.list_collection_names()
            print(f"\n📦 COLLECTIONS IN '{mongodb_db}':")
            for collection in sorted(collections):
                count = db[collection].count_documents({})
                print(f"   • {collection}: {count} documents")
        
        print("\n✅ YOUR MONGODB ATLAS CLUSTER IS WORKING PERFECTLY!")
        
    except Exception as e:
        print(f"\n⚠️ Could get cluster info: {e}")
    
    client.close()
    
except Exception as e:
    print(f"\n❌ FAILED TO CONNECT!")
    print(f"\nError: {e}")
    print("\n🔧 TROUBLESHOOTING STEPS:")
    print("   1. Check if you can login to https://cloud.mongodb.com")
    print("   2. Verify your password is correct")
    print("   3. Check Network Access settings in Atlas")
    print("      - Go to 'Network Access' → Add your IP or allow all (0.0.0.0/0)")
    print("   4. Verify cluster is active (not paused)")
    print("   5. Check database user has proper permissions")
    print("\n💡 TIP: If you can't access cloud.mongodb.com, try:")
    print("   - Reset your password")
    print("   - Use a different browser")
    print("   - Clear browser cache/cookies")
    print("   - Check if your internet allows accessing atlas.mongodb.com")

print("\n" + "=" * 80)
